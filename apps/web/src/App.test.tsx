import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { App } from './App'

vi.mock('./peerBroadcast', async () => {
  const actual = await vi.importActual<typeof import('./peerBroadcast')>('./peerBroadcast')
  return {
    ...actual,
    createLiveRoom: vi.fn(() => ({
      addStream: vi.fn(),
      removeStream: vi.fn(),
      leave: vi.fn(),
      getPeers: vi.fn(() => ({})),
      onPeerJoin: undefined,
      onPeerLeave: undefined,
      onPeerStream: undefined,
    })),
  }
})

describe('Instituto Tela Viva', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
  })

  it('apresenta a tese do aprendizado vivo e as jornadas por idade', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: /onde o conhecimento acontece vivo/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Escolha sua experiência' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /descobrir brincando/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /aprender fazendo/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /acompanhar o processo/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Profissionais ao vivo' })).toBeInTheDocument()
  })

  it('não preenche o catálogo com aulas, criadores ou audiência fictícios', () => {
    render(<App />)

    expect(screen.getAllByText('Nenhuma aula verificada foi carregada').length).toBeGreaterThan(0)
    expect(screen.getByText('Nenhum criador verificado foi carregado.')).toBeInTheDocument()
    expect(screen.getByText('Nenhum novo criador verificado foi carregado.')).toBeInTheDocument()
    expect(screen.queryByText('Marina Luz')).not.toBeInTheDocument()
    expect(screen.queryByText('Identidade visual do zero')).not.toBeInTheDocument()
    expect(screen.queryByText('1,2 mil')).not.toBeInTheDocument()
  })

  it('mantém filtros disponíveis sem inventar resultados', () => {
    render(<App />)
    fireEvent.change(screen.getByPlaceholderText(/busque por tema/i), { target: { value: 'Figma' } })
    fireEvent.click(screen.getByRole('button', { name: /filtros/i }))

    expect(screen.getByLabelText('Profissão')).toHaveValue('Todas')
    expect(screen.getByLabelText('Ferramenta')).toHaveValue('Todas')
    expect(screen.queryByText('Portfólio que conta uma história')).not.toBeInTheDocument()
  })

  it('abre autenticação sem depender de uma transmissão fictícia', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    const dialog = screen.getByRole('dialog', { name: 'Entre para assistir' })
    expect(within(dialog).getByLabelText('E-mail')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Senha')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Entrar na minha conta' })).toBeInTheDocument()
  })

  it('exige responsável ao configurar uma conta infantil', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }))

    const dialog = screen.getByRole('dialog', { name: 'Comece seu aprendizado' })
    fireEvent.click(within(dialog).getByRole('radio', { name: 'Criança' }))
    expect(within(dialog).getByLabelText('E-mail do responsável')).toBeRequired()
    expect(within(dialog).getByLabelText('Senha')).toHaveAttribute('minlength', '12')
  })
})

describe('Áreas operacionais sem dados fictícios', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
  })

  it('abre o painel do criador em estado vazio e identifica rascunhos locais', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Painel do criador' }))

    expect(screen.getByRole('heading', { name: /olá, criador/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Iniciar transmissão' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Configuração de preços' })).toBeInTheDocument()
    expect(screen.getAllByText('Sem dados verificados').length).toBeGreaterThan(0)
    expect(screen.queryByText('R$ 8.420')).not.toBeInTheDocument()
    expect(screen.queryByText('Marina Luz')).not.toBeInTheDocument()
  })

  it('abre a administração sem métricas, usuários ou moderação inventados', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Administração' }))

    expect(screen.getByRole('heading', { name: 'Visão geral' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Fila de moderação' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Métricas da plataforma' })).toBeInTheDocument()
    expect(screen.getByText(/nenhuma informação de moderação foi carregada/i)).toBeInTheDocument()
    expect(screen.queryByText('48.290')).not.toBeInTheDocument()
    expect(screen.queryByText('R$ 284 mil')).not.toBeInTheDocument()
    expect(screen.queryByText('Ana Ribeiro')).not.toBeInTheDocument()
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
    window.localStorage.clear()
    window.sessionStorage.clear()
    const display = makeStream('video')
    const audio = makeStream('audio')
    const camera = makeStream('video')
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
      getDisplayMedia: vi.fn().mockResolvedValue(display.stream),
      getUserMedia: vi.fn().mockImplementation((constraints: MediaStreamConstraints) =>
        Promise.resolve(constraints.video ? camera.stream : audio.stream)),
    } })
    Object.defineProperty(HTMLMediaElement.prototype, 'srcObject', { configurable: true, writable: true })
    Object.defineProperty(HTMLMediaElement.prototype, 'play', { configurable: true, value: vi.fn().mockResolvedValue(undefined) })
  })

  it('solicita autorização nativa, mostra preview e inicia a live', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar live' }))

    expect(screen.getByRole('dialog', { name: 'Prepare sua live' })).toBeInTheDocument()
    expect(screen.getByText(/não acessa nem controla seu computador/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Ver preview' }))

    await waitFor(() => expect(navigator.mediaDevices.getDisplayMedia).toHaveBeenCalledWith(expect.objectContaining({ video: true, audio: false })))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Iniciar transmissão' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar transmissão' }))
    expect(screen.getByText('● AO VIVO')).toBeInTheDocument()
  })

  it('liga a câmera e mostra a prévia no modo somente câmera', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar live' }))
    fireEvent.click(screen.getByRole('radio', { name: /Somente câmera/ }))

    await waitFor(() => expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith(expect.objectContaining({ video: expect.any(Object), audio: false })))
    await waitFor(() => expect(screen.getByLabelText('Prévia da câmera')).toBeInTheDocument())
    expect(screen.getByText('Câmera pronta')).toBeInTheDocument()
  })
})
