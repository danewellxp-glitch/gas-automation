export default function CoronaNavbar({ title, onToggleIconOnly, onToggleMobileSidebar }) {
  return (
    <header className="corona-navbar">
      <div className="corona-navbar-left">
        <button
          type="button"
          className="corona-navbar-btn corona-navbar-btn-mobile"
          onClick={() => onToggleMobileSidebar?.()}
          aria-label="Abrir menu"
        >
          ☰
        </button>

        <button
          type="button"
          className="corona-navbar-btn corona-navbar-btn-desktop"
          onClick={() => onToggleIconOnly?.()}
          aria-label="Alternar sidebar compacta"
          title="Alternar sidebar compacta"
        >
          ▦
        </button>

        {title ? <div className="corona-navbar-title">{title}</div> : null}
      </div>

      <div className="corona-navbar-right">
        <div className="corona-navbar-pill">Painel</div>
      </div>
    </header>
  )
}

