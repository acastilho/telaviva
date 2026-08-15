import { render, screen } from '@testing-library/react'
import { App } from './App'

describe('App', () => {
  it('apresenta a proposta de valor da TelaViva', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Veja. Aprenda. Apoie.' })).toBeInTheDocument()
    expect(screen.getByText(/profissionais trabalhando em tempo real/i)).toBeInTheDocument()
  })
})
