import { render, screen, waitFor } from '@testing-library/react'
import { authClient, type AuthSession } from './auth'
import { schedulingClient } from './scheduling'
import { VerifiedLiveViewer } from './VerifiedLiveViewer'

vi.mock('./auth', () => ({
  authClient: {
    restore: vi.fn(),
  },
}))

vi.mock('./scheduling', () => ({
  usesRemoteSchedulingApi: true,
  schedulingClient: {
    access: vi.fn(),
  },
}))

vi.mock('./LiveViewer', () => ({
  LiveViewer: ({ roomId }: { roomId: string }) => <div data-testid="live-viewer" data-room-id={roomId} />,
}))

vi.mock('./BrandMark', () => ({
  BrandMark: () => <span>Instituto Tela Viva</span>,
}))

const session: AuthSession = {
  accessToken: 'access-token',
  refreshToken: 'refresh-token',
  user: {
    id: 'viewer-id',
    email: 'viewer@example.com',
    role: 'VIEWER',
    audience: 'ADULT',
  },
}

describe('VerifiedLiveViewer authorization gate', () => {
  beforeEach(() => {
    vi.mocked(authClient.restore).mockReset()
    vi.mocked(schedulingClient.access).mockReset()
  })

  it('never resolves or joins a room when the viewer is unauthenticated', async () => {
    vi.mocked(authClient.restore).mockResolvedValue(null)

    render(<VerifiedLiveViewer streamId="public-stream-id" />)

    expect(await screen.findByRole('heading', { name: 'Entre para assistir' })).toBeInTheDocument()
    expect(schedulingClient.access).not.toHaveBeenCalled()
    expect(screen.queryByTestId('live-viewer')).not.toBeInTheDocument()
  })

  it('joins only the room returned by the authenticated stream access check', async () => {
    vi.mocked(authClient.restore).mockResolvedValue(session)
    vi.mocked(schedulingClient.access).mockResolvedValue({
      stream_id: 'public-stream-id',
      granted: true,
      reason: 'ENTITLED',
      entitlement_id: 'entitlement-id',
      checked_at: new Date().toISOString(),
      live_room_id: 'room-live-secure',
    })

    render(<VerifiedLiveViewer streamId="public-stream-id" />)

    await waitFor(() => expect(schedulingClient.access).toHaveBeenCalledWith('public-stream-id', 'access-token'))
    const viewer = await screen.findByTestId('live-viewer')
    expect(viewer).toHaveAttribute('data-room-id', 'room-live-secure')
  })
})
