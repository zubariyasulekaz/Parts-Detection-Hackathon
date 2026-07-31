import { useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/common/EmptyState'
import { PageContainer } from '@/components/layout/PageContainer'

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <PageContainer className="py-24">
      <EmptyState
        title="Page not found"
        description="The page you're looking for doesn't exist or has moved."
        action={
          <button
            type="button"
            onClick={() => navigate('/')}
            className="mt-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            Go to Landing Page
          </button>
        }
      />
    </PageContainer>
  )
}
