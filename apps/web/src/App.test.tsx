import { fireEvent, render, screen, within } from '@testing-library/react'
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
