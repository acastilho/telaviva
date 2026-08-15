import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { App } from './App'

describe('Dashboard do espectador', () => {
  it('exibe as principais áreas de descoberta', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: /o que você quer aprender hoje/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Profissionais ao vivo' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Próximas aulas' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Criadores populares' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Categorias' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Acabaram de chegar' })).toBeInTheDocument()
  })

  it('pesquisa por profissional, tema ou ferramenta', () => {
    render(<App />)
    fireEvent.change(screen.getByPlaceholderText(/busque por tema/i), { target: { value: 'Figma' } })

    expect(screen.getByText('Identidade visual do zero')).toBeInTheDocument()
    expect(screen.queryByText('Cerâmica: torneando uma xícara')).not.toBeInTheDocument()
    expect(screen.getByText('Portfólio que conta uma história')).toBeInTheDocument()
  })

  it('combina filtros e permite limpá-los', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /filtros/i }))
    fireEvent.change(screen.getByLabelText('Preço'), { target: { value: 'Gratuito' } })
    fireEvent.change(screen.getByLabelText('Quando'), { target: { value: 'Agendado' } })

    expect(screen.getByText('Pão de fermentação natural')).toBeInTheDocument()
    expect(screen.queryByText('Mixando vocais em casa')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Limpar filtros' }))
    expect(screen.getByText('Mixando vocais em casa')).toBeInTheDocument()
  })

  it('exige login ao tentar assistir a uma transmissão', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Assistir Identidade visual do zero' }))

    const dialog = screen.getByRole('dialog', { name: 'Entre para assistir' })
    expect(within(dialog).getByText('Assistir transmissões requer login.')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Fechar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('Estúdio de transmissão', () => {
  const makeStream = (kind: 'video' | 'audio') => {
    const track = { enabled: true, stop: vi.fn(), addEventListener: vi.fn() }
    return {
      stream: {
        getTracks: () => [track],
        getVideoTracks: () => kind === 'video' ? [track] : [],
        getAudioTracks: () => kind === 'audio' ? [track] : [],
      } as unknown as MediaStream,
      track,
    }
  }

  beforeEach(() => {
    const display = makeStream('video')
    const audio = makeStream('audio')
    const camera = makeStream('video')
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
      getDisplayMedia: vi.fn().mockResolvedValue(display.stream),
      getUserMedia: vi.fn().mockImplementation((constraints: MediaStreamConstraints) =>
        Promise.resolve(constraints.video ? camera.stream : audio.stream)),
    } })
    Object.defineProperty(HTMLMediaElement.prototype, 'srcObject', { configurable: true, writable: true })
  })

  it('solicita autorização nativa, mostra preview e controla o ciclo da live', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar live' }))

    expect(screen.getByRole('dialog', { name: 'Prepare sua live' })).toBeInTheDocument()
    expect(screen.getByText(/não acessa nem controla seu computador/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Ver preview' }))

    await waitFor(() => expect(navigator.mediaDevices.getDisplayMedia).toHaveBeenCalledWith({ video: true, audio: false }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Iniciar transmissão' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar transmissão' }))
    expect(screen.getByText('● AO VIVO')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Pausar' }))
    expect(screen.getByText('Transmissão pausada')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retomar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Silenciar' }))
    expect(screen.getByRole('button', { name: 'Ativar microfone' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Finalizar' }))
    expect(screen.getByText('Live finalizada')).toBeInTheDocument()
  })

  it('permite layout somente câmera sem solicitar compartilhamento de tela', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar live' }))
    fireEvent.click(screen.getByRole('radio', { name: /somente câmera/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Ver preview' }))

    await waitFor(() => expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ video: true, audio: false }))
    expect(navigator.mediaDevices.getDisplayMedia).not.toHaveBeenCalled()
    expect(await screen.findByLabelText('Prévia da câmera')).toBeInTheDocument()
  })

  it('informa quando o compartilhamento não é autorizado', async () => {
    vi.mocked(navigator.mediaDevices.getDisplayMedia).mockRejectedValueOnce(new DOMException('Denied'))
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar live' }))
    fireEvent.click(screen.getByRole('button', { name: 'Escolher fonte' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/não autorizado/i)
  })
})
