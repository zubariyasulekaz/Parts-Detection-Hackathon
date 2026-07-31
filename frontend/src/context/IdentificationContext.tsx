import { createContext, useCallback, useContext, useMemo, useReducer, useRef, type ReactNode } from 'react'
import { identify as runPipeline } from '@/services/identificationService'
import type { IdentificationResult, IdentificationStatus, ProcessingStageKey } from '@/types/identification'

/**
 * Owns the state the primary user journey must survive across route
 * changes: the queued/uploaded image, the identification result, the
 * current processing stage, and which candidate the user has
 * selected/confirmed.
 */
interface State {
  status: IdentificationStatus
  pendingFile: File | null
  pendingIsSample: boolean
  uploadedImageUrl: string | null
  currentStage: ProcessingStageKey | null
  result: IdentificationResult | null
  selectedSku: string | null
  error: string | null
}

type Action =
  | { type: 'SET_PENDING'; file: File; isSample: boolean }
  | { type: 'START'; uploadedImageUrl: string }
  | { type: 'STAGE'; stage: ProcessingStageKey }
  | { type: 'SUCCESS'; result: IdentificationResult }
  | { type: 'ERROR'; message: string }
  | { type: 'SELECT'; sku: string }
  | { type: 'RESET' }

const initialState: State = {
  status: 'idle',
  pendingFile: null,
  pendingIsSample: false,
  uploadedImageUrl: null,
  currentStage: null,
  result: null,
  selectedSku: null,
  error: null,
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_PENDING':
      return { ...initialState, pendingFile: action.file, pendingIsSample: action.isSample }
    case 'START':
      return { ...state, status: 'processing', uploadedImageUrl: action.uploadedImageUrl, currentStage: null, error: null }
    case 'STAGE':
      return { ...state, currentStage: action.stage }
    case 'SUCCESS':
      return {
        ...state,
        status: action.result.requiresConfirmation ? 'ambiguous' : 'success',
        result: action.result,
        selectedSku: action.result.selectedSku,
      }
    case 'ERROR':
      return { ...state, status: 'error', error: action.message }
    case 'SELECT':
      return { ...state, selectedSku: action.sku, status: 'success' }
    case 'RESET':
      return initialState
    default:
      return state
  }
}

interface IdentificationContextValue extends State {
  /** Stash a chosen/sample file for the /identify page to run, resetting any prior result. */
  setPendingUpload: (file: File, isSample?: boolean) => void
  /** Runs the pipeline against the currently pending file. Throws if none is queued. */
  runIdentification: () => Promise<IdentificationResult>
  selectCandidate: (sku: string) => void
  reset: () => void
}

const IdentificationContext = createContext<IdentificationContextValue | null>(null)

export function IdentificationProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const objectUrlRef = useRef<string | null>(null)
  const stateRef = useRef(state)
  stateRef.current = state

  const setPendingUpload = useCallback((file: File, isSample = false) => {
    dispatch({ type: 'SET_PENDING', file, isSample })
  }, [])

  const runIdentification = useCallback(async () => {
    const { pendingFile, pendingIsSample } = stateRef.current
    if (!pendingFile) {
      throw new Error('No image is queued for identification.')
    }

    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    const uploadedImageUrl = URL.createObjectURL(pendingFile)
    objectUrlRef.current = uploadedImageUrl
    dispatch({ type: 'START', uploadedImageUrl })

    try {
      const result = await runPipeline(pendingFile, uploadedImageUrl, {
        useSampleScenario: pendingIsSample,
        onStage: (stage) => dispatch({ type: 'STAGE', stage }),
      })
      dispatch({ type: 'SUCCESS', result })
      return result
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Identification failed. Please try again.'
      dispatch({ type: 'ERROR', message })
      throw error
    }
  }, [])

  const selectCandidate = useCallback((sku: string) => dispatch({ type: 'SELECT', sku }), [])

  const reset = useCallback(() => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    objectUrlRef.current = null
    dispatch({ type: 'RESET' })
  }, [])

  const value = useMemo<IdentificationContextValue>(
    () => ({ ...state, setPendingUpload, runIdentification, selectCandidate, reset }),
    [state, setPendingUpload, runIdentification, selectCandidate, reset],
  )

  return <IdentificationContext.Provider value={value}>{children}</IdentificationContext.Provider>
}

export function useIdentification(): IdentificationContextValue {
  const ctx = useContext(IdentificationContext)
  if (!ctx) {
    throw new Error('useIdentification must be used within an IdentificationProvider')
  }
  return ctx
}
