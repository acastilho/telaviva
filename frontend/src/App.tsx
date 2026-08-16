const categories = ['Programação', 'Inteligência Artificial', 'Design', 'Dados', 'Música', 'Arquitetura']

function App() {
  return (
    <main>
      <nav className="nav">
        <a className="brand" href="#top"><span>TV</span>Tela Viva</a>
        <div><a href="#explorar">Explorar</a><a href="#como-funciona">Como funciona</a></div>
        <button className="secondary">Entrar</button>
      </nav>

      <section className="hero" id="top">
        <div>
          <p className="eyebrow">CONHECIMENTO ACONTECENDO AGORA</p>
          <h1>Veja profissionais<br/><em>criando ao vivo.</em></h1>
          <p className="lede">Observe processos reais, faça perguntas e apoie quem transforma experiência em aprendizado.</p>
          <div className="actions"><button>Explorar transmissões</button><button className="secondary">Quero ensinar</button></div>
        </div>
        <aside className="live-card">
          <div className="preview"><span className="live">● AO VIVO</span><div className="play">▶</div></div>
          <p className="eyebrow">PROGRAMAÇÃO · INTERMEDIÁRIO</p>
          <h2>Construindo uma API escalável</h2>
          <p>Marina Costa · 284 assistindo</p>
        </aside>
      </section>

      <section className="section" id="explorar">
        <p className="eyebrow">ENCONTRE SUA PRÓXIMA HABILIDADE</p>
        <h2>Aprenda acompanhando o trabalho real.</h2>
        <div className="categories">{categories.map(category => <button className="chip" key={category}>{category}</button>)}</div>
      </section>

      <section className="steps" id="como-funciona">
        <article><b>01</b><h3>Encontre</h3><p>Descubra criadores, profissões e ferramentas relevantes.</p></article>
        <article><b>02</b><h3>Participe</h3><p>Assista, converse e tire dúvidas durante o processo.</p></article>
        <article><b>03</b><h3>Apoie</h3><p>Compre aulas ou envie uma contribuição ao profissional.</p></article>
      </section>
    </main>
  )
}

export default App
