import { fireEvent, render, screen, within } from '@testing-library/react'
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

  it('falha de forma fechada quando a API de aulas não está configurada', () => {
    render(<App />)

    expect(screen.getByText('Não foi possível consultar as aulas')).toBeInTheDocument()
    expect(screen.getAllByText('API de aulas não configurada.').length).toBeGreaterThan(0)
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
  beforeEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
      getDisplayMedia: vi.fn(),
      getUserMedia: vi.fn(),
    } })
  })

  it('não abre o estúdio sem uma fonte oficial de aulas', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar live' }))

    expect(screen.getByText('A API de aulas precisa estar configurada para iniciar uma transmissão.')).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Prepare sua live' })).not.toBeInTheDocument()
    expect(navigator.mediaDevices.getDisplayMedia).not.toHaveBeenCalled()
    expect(navigator.mediaDevices.getUserMedia).not.toHaveBeenCalled()
  })

  it('não inventa uma aula ativa para liberar câmera ou compartilhamento', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar live' }))

    expect(screen.queryByRole('button', { name: 'Ver preview' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Iniciar transmissão' })).not.toBeInTheDocument()
    expect(screen.queryByText('● AO VIVO')).not.toBeInTheDocument()
  })
})
