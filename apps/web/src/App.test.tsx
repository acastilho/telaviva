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

  it('navega pela biblioteca, filtra origens e abre o replay com progresso', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Minha biblioteca' }))
    expect(screen.getByRole('heading', { name: 'Minhas aulas' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'De onde você parou' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Compradas' }))
    expect(screen.getAllByText('Identidade visual do zero')).toHaveLength(2)
    expect(screen.queryByText('Luz natural em retratos')).not.toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'Assistir gravação Identidade visual do zero' })[0])
    expect(screen.getByRole('region', { name: 'Player de Identidade visual do zero' })).toBeInTheDocument()
    expect(screen.getByText(/42% assistido/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reproduzir' }))
    expect(screen.getByText(/52% assistido/)).toBeInTheDocument()
  })
})

describe('Painel do criador', () => {
  it('reúne operação, público, monetização e histórico do criador', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Painel do criador' }))

    expect(screen.getByRole('heading', { name: /olá, marina/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Iniciar transmissão' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Próximas aulas' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Gravações' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Seus alunos' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Seguidores' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Vendas' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Gorjetas' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Histórico financeiro' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Configuração de preços' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /gráfico de receita/i })).toBeInTheDocument()
  })

  it('configura preços e abre o estúdio a partir do painel', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Painel do criador' }))
    fireEvent.click(screen.getByRole('button', { name: 'Configurar preços' }))

    const dialog = screen.getByRole('dialog', { name: 'Configurar preços' })
    fireEvent.change(within(dialog).getByLabelText('Preço padrão da aula'), { target: { value: '99,00' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Salvar preços' }))
    expect(screen.getByRole('status')).toHaveTextContent('Preços atualizados com sucesso.')

    fireEvent.click(screen.getByRole('button', { name: 'Iniciar transmissão' }))
    expect(screen.getByRole('dialog', { name: 'Prepare sua live' })).toBeInTheDocument()
  })
})

describe('Painel administrativo', () => {
  it('reúne todas as áreas de administração da plataforma', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Administração' }))

    expect(screen.getByRole('heading', { name: 'Visão geral' })).toBeInTheDocument()
    const navigation = screen.getByRole('navigation', { name: 'Navegação administrativa' })
    for (const area of ['Usuários', 'Criadores', 'Transmissões', 'Gravações', 'Pagamentos', 'Denúncias', 'Categorias', 'Comissões', 'Auditoria', 'Métricas', 'Bloqueios', 'Moderação']) {
      expect(within(navigation).getByRole('button', { name: area })).toBeInTheDocument()
    }
    expect(screen.getByRole('heading', { name: 'Usuários recentes' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Fila de moderação' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Métricas da plataforma' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Audiência das transmissões ao vivo' })).toBeInTheDocument()
  })

  it('pesquisa, filtra e resolve itens da fila de moderação', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Administração' }))

    fireEvent.change(screen.getByLabelText('Buscar na administração'), { target: { value: 'direitos autorais' } })
    expect(screen.getByText('Revisão por direitos autorais')).toBeInTheDocument()
    expect(screen.queryByText('Mensagem ofensiva no chat')).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Buscar na administração'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Filtrar status'), { target: { value: 'Em análise' } })
    expect(screen.getByText('Mensagem ofensiva no chat')).toBeInTheDocument()
    expect(screen.queryByText('Validação de perfil profissional')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Revisar Mensagem ofensiva no chat' }))
    expect(screen.queryByText('Mensagem ofensiva no chat')).not.toBeInTheDocument()
  })

  it('volta para a TelaViva pelo cabeçalho administrativo', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Administração' }))
    fireEvent.click(screen.getByRole('button', { name: 'Voltar ao início' }))
    expect(screen.getByRole('heading', { name: /o que você quer aprender hoje/i })).toBeInTheDocument()
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

  it('permite ao criador habilitar e desabilitar canais de interação', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar live' }))

    const chat = screen.getByRole('checkbox', { name: 'Chat' })
    expect(chat).toBeChecked()
    fireEvent.click(chat)
    expect(chat).not.toBeChecked()
    expect(screen.getByRole('status')).toHaveTextContent('2 de 3 canais habilitados')
  })
})
