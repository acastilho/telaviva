const roles = [
  ['Crie', 'Transmita seu ofício e forme uma comunidade.'],
  ['Aprenda', 'Acompanhe profissionais trabalhando em tempo real.'],
  ['Apoie', 'Contribua diretamente com quem compartilha conhecimento.'],
]

export function App() {
  return (
    <main>
      <nav aria-label="Navegação principal">
        <strong>TelaViva</strong>
        <a href="#como-funciona">Como funciona</a>
      </nav>
      <section className="hero">
        <p className="eyebrow">Trabalho real. Conhecimento ao vivo.</p>
        <h1>Veja. Aprenda. Apoie.</h1>
        <p className="intro">
          Entre nos bastidores do trabalho de profissionais, converse em tempo real e ajude
          criadores a continuarem ensinando.
        </p>
        <a className="button" href="#como-funciona">Conheça a TelaViva</a>
      </section>
      <section id="como-funciona" className="cards" aria-label="Como funciona">
        {roles.map(([title, description]) => (
          <article key={title}>
            <h2>{title}</h2>
            <p>{description}</p>
          </article>
        ))}
      </section>
    </main>
  )
}
