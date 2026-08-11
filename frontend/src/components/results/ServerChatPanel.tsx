import { CircleHelp, RotateCcw, SkipForward, Sparkles, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { answerChat, startChat, undoChat } from '@/api/partpilotApi'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { DisambiguationAnswer } from '@/services/disambiguation'
import { formatPercent } from '@/utils/format'
import type { ChatStateDTO } from '@/types/api'
import type { IdentificationCandidate } from '@/types/identification'

/**
 * The server-driven guided chat, presented as a messenger window - the way a
 * food-delivery support chat looks: assistant header up top, a scrolling
 * thread of bubbles (assistant left with an avatar, user right), a typing
 * indicator between turns, and the tappable answers in a quick-reply tray
 * pinned to the bottom.
 *
 * Every turn is a round trip to the backend chat API (`/chat/start`,
 * `/chat/{id}/answer`, `/chat/{id}/undo`) - the server owns the session and
 * this component only renders the state it returns. Selected in live mode by
 * `VITE_CHAT_API=true`; mock mode uses the local `GuidedDisambiguation`
 * flow, which the API mirrors one-for-one.
 */

/** Minimum time the typing dots stay visible, so fast responses still read as a reply being written. */
const TYPING_MS = 550

interface ServerChatPanelProps {
  candidates: IdentificationCandidate[]
  onRemainingChange: (skus: string[]) => void
  onResolved: (sku: string, answers: DisambiguationAnswer[]) => void
  onAnswersChange?: (answers: DisambiguationAnswer[]) => void
  onFinished?: (remainingSkus: string[]) => void
  onOverrideSelection?: (sku: string) => void
  selectedSku?: string | null
}

/**
 * The trail shape the results page shares with the local flow. Skipped turns
 * are part of the transcript but not of the answer trail - they narrowed
 * nothing, so reporting them as answers would overstate how the pick was made.
 */
function toAnswers(chat: ChatStateDTO): DisambiguationAnswer[] {
  return chat.answers
    .filter((entry) => !entry.skipped)
    .map((entry) => ({
      facet: entry.facet as DisambiguationAnswer['facet'],
      label: entry.label,
      skus: entry.skus,
    }))
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function BotAvatar() {
  return (
    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/15 text-accent-soft">
      <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
    </span>
  )
}

/** An assistant message: avatar on the left, bubble beside it. */
function BotMessage({ tone = 'default', children }: { tone?: 'default' | 'success' | 'caution'; children: ReactNode }) {
  return (
    <div className="flex animate-fade-slide-up items-start gap-2">
      <BotAvatar />
      <div
        className={`max-w-[80%] rounded-2xl rounded-tl-sm border px-3.5 py-2.5 ${
          tone === 'success'
            ? 'border-success/30 bg-success-muted/40'
            : tone === 'caution'
              ? 'border-warning/30 bg-warning-muted/40'
              : 'border-border-strong bg-surface-2'
        }`}
      >
        {children}
      </div>
    </div>
  )
}

/**
 * A user message: blue bubble on the right, like every messenger. A skipped
 * question ("Not sure") is muted rather than blue - it belongs in the
 * transcript, but it did not narrow anything and should not read as a choice.
 */
function UserMessage({ muted = false, children }: { muted?: boolean; children: ReactNode }) {
  return (
    // `w-full` matters: inside an `items-end` column this element would
    // otherwise shrink to min-content and wrap the label mid-word ("Not
    // sure" becoming two squeezed lines).
    <div className="flex w-full animate-fade-slide-up justify-end">
      <div
        className={`max-w-[80%] rounded-2xl rounded-tr-sm px-3.5 py-2.5 ${
          muted ? 'border border-border-strong bg-surface-2 text-muted' : 'bg-accent text-white'
        }`}
      >
        {children}
      </div>
    </div>
  )
}

/** Three pulsing dots - the assistant is "typing" while the server decides. */
function TypingMessage() {
  return (
    <div className="flex items-start gap-2">
      <BotAvatar />
      <div
        aria-label="PartPilot is typing"
        className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-border-strong bg-surface-2 px-4 py-3"
      >
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            style={{ animationDelay: `${delay}ms` }}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-subtle"
          />
        ))}
      </div>
    </div>
  )
}

export function ServerChatPanel({
  candidates,
  onRemainingChange,
  onResolved,
  onAnswersChange,
  onFinished,
  onOverrideSelection,
  selectedSku = null,
}: ServerChatPanelProps) {
  const [chat, setChat] = useState<ChatStateDTO | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // The user's tap, echoed as a right-hand bubble immediately - their message
  // should not wait for the server's reply to appear.
  const [pending, setPending] = useState<string | null>(null)
  // The user chose "show me the matches" - stop asking client-side; the
  // server session stays valid so "Start over" can resume it.
  const [skippedAll, setSkippedAll] = useState(false)
  // Whether any single question was skipped with "Not sure" - drives the
  // gentler "best guess" copy when the questions run out.
  const [skippedSome, setSkippedSome] = useState(false)
  // Only announce a resolution once per resolved SKU, not on every render.
  const announcedRef = useRef<string | null>(null)

  const bySku = (sku: string) => candidates.find((candidate) => candidate.sku === sku)

  function propagate(state: ChatStateDTO, stopAsking = skippedAll) {
    setChat(state)
    const answers = toAnswers(state)
    onAnswersChange?.(answers)
    onRemainingChange(state.remaining_skus)
    if (state.resolved_sku && announcedRef.current !== state.resolved_sku) {
      announcedRef.current = state.resolved_sku
      onResolved(state.resolved_sku, answers)
    }
    if (state.status !== 'asking' || stopAsking) onFinished?.(state.remaining_skus)
  }

  async function run(call: () => Promise<ChatStateDTO>, echo: string | null = null, stopAsking?: boolean) {
    setBusy(true)
    setError(null)
    setPending(echo)
    try {
      // Hold the typing dots for a beat even when the server replies fast -
      // an instant reply doesn't read as a conversation.
      const [state] = await Promise.all([call(), sleep(echo === null ? 0 : TYPING_MS)])
      propagate(state, stopAsking)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The chat service is unreachable.')
    } finally {
      setPending(null)
      setBusy(false)
    }
  }

  useEffect(() => {
    // One session per candidate set; candidates never change while mounted.
    void run(() => startChat(candidates.map(({ sku, similarity }) => ({ sku, similarity }))))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const resolvedSku = chat?.resolved_sku ?? null
  const resolved = resolvedSku ? bySku(resolvedSku) : null
  const mismatch = chat?.mismatch ?? null
  const isMismatchedResolution = Boolean(
    resolvedSku && mismatch && resolvedSku === mismatch.best_survivor_sku,
  )
  const question = skippedAll ? null : (chat?.question ?? null)
  const remainingCount = chat?.remaining_skus.length ?? candidates.length

  if (error) {
    return (
      <section className="shadow-card rounded-xl border border-warning/30 bg-surface p-5">
        <p className="text-sm font-semibold text-foreground">The guided chat is unavailable.</p>
        <p className="mt-1 text-xs text-muted">{error}</p>
        <p className="mt-1 text-xs text-muted">
          Compare the candidates below and pick the one that matches your part.
        </p>
      </section>
    )
  }

  return (
    <section
      aria-label="Narrow down the match"
      aria-busy={busy}
      className="shadow-card flex flex-col overflow-hidden rounded-xl border border-accent/25 bg-surface"
    >
      {/* Messenger header: who you're talking to, and where the narrowing stands. */}
      <div className="mx-auto flex w-full max-w-2xl items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-9 w-9 items-center justify-center rounded-full bg-accent/15 text-accent-soft">
            <Sparkles className="h-4.5 w-4.5" aria-hidden="true" />
            <span className="absolute right-0 bottom-0 h-2.5 w-2.5 rounded-full border-2 border-surface bg-success" />
          </span>
          <div>
            <p className="text-sm font-bold text-foreground">PartPilot Assistant</p>
            <p className="text-xs text-muted">
              {busy ? 'typing…' : resolvedSku ? 'match found' : 'narrowing your match'}
            </p>
          </div>
        </div>
        <StatusBadge variant={resolvedSku ? 'success' : 'info'}>
          {resolvedSku ? '1 match' : `${remainingCount} possible matches`}
        </StatusBadge>
      </div>

      {/* The thread grows with the conversation rather than scrolling inside a
          fixed-height box: these exchanges run two to four turns, and a
          nested scroll area would hide earlier questions behind a scrollbar
          the user has to find. The page scrolls; the transcript stays whole.

          Capped and centred: at the results page's full width the two sides
          of the conversation end up a screen apart, which reads as scattered
          elements rather than a back-and-forth. A messenger column keeps
          question and answer within sight of each other. */}
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-3 px-4 py-4">
        <BotMessage>
          <p className="text-sm text-foreground">
            Hi! Your photo is visually close to <span className="font-semibold">{candidates.length} parts</span> in
            our catalog. A couple of quick questions will pin down the right one.
          </p>
        </BotMessage>

        {chat?.answers.map((entry, index) => (
          <div key={`${entry.facet}-${index}`} className="flex flex-col gap-1.5">
            <BotMessage>
              <p className="text-sm text-foreground">{entry.prompt}</p>
            </BotMessage>
            <UserMessage muted={entry.skipped}>
              <p className="text-sm font-semibold whitespace-nowrap">{entry.label}</p>
            </UserMessage>
            <div className="flex justify-end">
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  announcedRef.current = null
                  void run(() => undoChat(chat.session_id, index), '')
                }}
                aria-label={`Change your answer: ${entry.label}`}
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium text-subtle transition-colors hover:text-foreground"
              >
                <RotateCcw className="h-3 w-3" aria-hidden="true" />
                Change
              </button>
            </div>
          </div>
        ))}

        {/* The just-tapped answer, echoed instantly while the server thinks. */}
        {pending !== null && pending !== '' && (
          <UserMessage muted={pending === 'Not sure'}>
            <p className="text-sm font-semibold whitespace-nowrap">{pending}</p>
          </UserMessage>
        )}

        {busy && <TypingMessage />}

        {!busy && question && (
          <BotMessage>
            <p className="text-sm font-semibold text-foreground">{question.prompt}</p>
            {question.hint && <p className="mt-0.5 text-xs text-muted">{question.hint}</p>}
          </BotMessage>
        )}

        {!busy && resolvedSku && (
          <BotMessage tone={isMismatchedResolution ? 'caution' : 'success'}>
            {isMismatchedResolution && mismatch ? (
              <>
                <p className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-warning-soft">
                  <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />
                  Visual mismatch
                </p>
                <p className="text-sm text-foreground">
                  Based on your answers, this is{' '}
                  <span className="font-mono font-semibold">{resolvedSku}</span>
                  {resolved ? (
                    <>
                      {' '}
                      - <span className="font-semibold">{resolved.productName}</span>
                    </>
                  ) : null}
                  . But your uploaded photo is a{' '}
                  <span className="font-semibold text-foreground">
                    {formatPercent(mismatch.visual_leader_similarity)}
                  </span>{' '}
                  visual match for{' '}
                  <span className="font-mono font-semibold text-foreground">
                    {mismatch.visual_leader_sku}
                  </span>{' '}
                  instead (this one scores {formatPercent(mismatch.best_survivor_similarity)}). Could you
                  verify again, or would this product work for you?
                </p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => onOverrideSelection?.(resolvedSku)}
                    aria-pressed={selectedSku === resolvedSku}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                      selectedSku === resolvedSku
                        ? 'border-warning bg-warning text-white'
                        : 'border-warning/40 bg-surface text-warning-soft hover:bg-warning-muted/40'
                    }`}
                  >
                    Yes, use {resolvedSku}
                  </button>
                  <button
                    type="button"
                    onClick={() => onOverrideSelection?.(mismatch.visual_leader_sku)}
                    aria-pressed={selectedSku === mismatch.visual_leader_sku}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                      selectedSku === mismatch.visual_leader_sku
                        ? 'border-accent bg-accent text-white'
                        : 'border-border-strong bg-surface-2 text-foreground hover:border-accent/50'
                    }`}
                  >
                    Show me {mismatch.visual_leader_sku} instead
                  </button>
                </div>
              </>
            ) : (
              <p className="text-sm text-foreground">
                That leaves one match: <span className="font-mono font-semibold">{resolvedSku}</span>
                {resolved ? (
                  <>
                    {' '}
                    - <span className="font-semibold">{resolved.productName}</span>
                  </>
                ) : null}
              </p>
            )}
            <p className="mt-1 text-xs text-muted">
              Selected below. Change any answer above if that doesn&rsquo;t look right.
            </p>
          </BotMessage>
        )}

        {!busy && chat && !resolvedSku && !question && (
          <BotMessage>
            {(skippedAll || skippedSome) && bySku(chat.remaining_skus[0] ?? '') ? (
              <p className="text-sm text-foreground">
                No problem - since you weren&rsquo;t sure, here&rsquo;s our best guess based on your photo:{' '}
                <span className="font-mono font-semibold">{chat.remaining_skus[0]}</span> -{' '}
                <span className="font-semibold">{bySku(chat.remaining_skus[0])?.productName}</span> (
                {formatPercent(bySku(chat.remaining_skus[0])?.similarity ?? 0)} visual match).
              </p>
            ) : (
              <p className="text-sm text-foreground">
                {chat.remaining_skus.length} candidates are still possible, and the catalog has nothing
                further that tells them apart. Compare the photos below and pick the one that matches
                your part.
              </p>
            )}
            {(chat.answers.length > 0 || skippedAll) && (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setSkippedAll(false)
                  setSkippedSome(false)
                  announcedRef.current = null
                  void run(() => undoChat(chat.session_id, 0), '')
                }}
                className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg border border-border-strong px-3 py-1.5 text-xs font-semibold text-foreground transition-colors hover:border-accent/50"
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                Start over
              </button>
            )}
          </BotMessage>
        )}

      </div>

      {/* Quick-reply tray, pinned under the thread - where a messenger's input
          bar would be. The user never types; these chips ARE the input. */}
      {question && chat && (
        <div className="mx-auto w-full max-w-2xl border-t border-border px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            {question.options.map((option, index) => (
              <button
                key={option.label}
                type="button"
                disabled={busy}
                onClick={() =>
                  void run(() => answerChat(chat.session_id, { optionIndex: index }), option.label)
                }
                className="rounded-full border border-accent/40 bg-surface px-4 py-2 text-sm font-semibold text-accent-soft transition-colors hover:border-accent hover:bg-accent/10 disabled:opacity-50"
              >
                {option.label}
                <span className="ml-1.5 font-mono text-xs font-normal text-subtle">{option.skus.length}</span>
              </button>
            ))}
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setSkippedSome(true)
                void run(() => answerChat(chat.session_id, { skip: true }), 'Not sure')
              }}
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-medium text-subtle transition-colors hover:text-foreground disabled:opacity-50"
            >
              <CircleHelp className="h-4 w-4" aria-hidden="true" />
              Not sure
            </button>
          </div>
          <div className="mt-2 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => {
                setSkippedAll(true)
                onFinished?.(chat.remaining_skus)
              }}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-subtle transition-colors hover:text-foreground"
            >
              <SkipForward className="h-3.5 w-3.5" aria-hidden="true" />
              Skip questions - show me the matches
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
