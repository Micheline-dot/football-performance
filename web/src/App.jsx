import { useEffect, useState } from 'react'
import './App.css'

const API_BASE_URL =
  import.meta.env.VITE_API_URL || 'https://football-performance.onrender.com'

function App() {
  // ==============================
  // ESTADO GENERAL
  // ==============================

  const [pagina, setPagina] = useState('inicio')

  // Estado de la API
  const [estadoAPI, setEstadoAPI] = useState('Comprobando...')
  const [visionArtificial, setVisionArtificial] = useState('...')
  const [tracking, setTracking] = useState('...')

  // Los jugadores se obtienen directamente del análisis de visión artificial.

  // Un solo análisis activo.
  // Cuando se analiza un nuevo video, reemplaza al anterior.
  const [analisisActual, setAnalisisActual] = useState(() => {
    try {
      const guardado = localStorage.getItem('footballPerformanceAnalisisActual')
      return guardado ? JSON.parse(guardado) : null
    } catch {
      return null
    }
  })

  const [mostrarSesionForm, setMostrarSesionForm] = useState(false)
  const [nombreAnalisis, setNombreAnalisis] = useState('')

  // ==============================
  // CONEXIÓN CON FASTAPI
  // ==============================

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/estado`)
      .then((respuesta) => {
        if (!respuesta.ok) {
          throw new Error('Error de conexión')
        }

        return respuesta.json()
      })
      .then((datos) => {
        setEstadoAPI(datos.estado || 'Disponible')
        setVisionArtificial(datos.vision_artificial || 'YOLO')
        setTracking(datos.tracking || 'ByteTrack')
      })
      .catch(() => {
        setEstadoAPI('Sin conexión')
        setVisionArtificial('No disponible')
        setTracking('No disponible')
      })
  }, [])

  // ==============================
  // ANÁLISIS DE VIDEO
  // ==============================

  const [videoSeleccionado, setVideoSeleccionado] = useState(null)
  const [analizando, setAnalizando] = useState(false)

  const [resultadoVideo, setResultadoVideo] = useState(() => {
    return localStorage.getItem('footballPerformanceVideo') || null
  })

  const [mensajeAnalisis, setMensajeAnalisis] = useState('')

  // Se conserva el último análisis para que los datos no desaparezcan
  // al cambiar de página o actualizar el navegador.
  const [metricasReales, setMetricasReales] = useState(() => {
    try {
      const guardadas = localStorage.getItem('footballPerformanceMetricas')
      return guardadas
        ? JSON.parse(guardadas)
        : {
            jugadores_detectados: 0,
            velocidad_maxima: 0,
            distancia_maxima: 0,
            jugadores: [],
          }
    } catch {
      return {
        jugadores_detectados: 0,
        velocidad_maxima: 0,
        distancia_maxima: 0,
        jugadores: [],
      }
    }
  })

  useEffect(() => {
    localStorage.setItem(
      'footballPerformanceMetricas',
      JSON.stringify(metricasReales)
    )
  }, [metricasReales])

  useEffect(() => {
    if (resultadoVideo) {
      localStorage.setItem('footballPerformanceVideo', resultadoVideo)
    }
  }, [resultadoVideo])

  useEffect(() => {
    if (analisisActual) {
      localStorage.setItem(
        'footballPerformanceAnalisisActual',
        JSON.stringify(analisisActual)
      )
    } else {
      localStorage.removeItem('footballPerformanceAnalisisActual')
    }
  }, [analisisActual])

  // ==============================
  // FUNCIONES DE ANÁLISIS DE VIDEO
  // ==============================

  const seleccionarVideo = (e) => {
    const archivo = e.target.files?.[0]

    if (!archivo) {
      return
    }

    setVideoSeleccionado(archivo)
    setResultadoVideo(null)
    setMensajeAnalisis('')
  }

  const descargarVideo = () => {
    if (!resultadoVideo) {
      alert('No hay un video analizado para descargar.')
      return
    }

    const nombre = (nombreAnalisis || 'football-performance-analisis')
      .replace(/[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ_-]+/g, '_')
      .replace(/^_+|_+$/g, '')

    // FastAPI entrega el archivo con Content-Disposition: attachment,
    // por lo que Chrome inicia una descarga real en lugar de reproducirlo.
    window.location.href = `${API_BASE_URL}/api/descargar-video?nombre=${encodeURIComponent(nombre)}`
  }

  const analizarVideo = async () => {
    if (!nombreAnalisis.trim()) {
      alert('Escriba un nombre para el análisis.')
      return
    }

    if (!videoSeleccionado) {
      alert('Seleccione un video primero.')
      return
    }

    setAnalizando(true)
    setResultadoVideo(null)
    setMensajeAnalisis('⏳ Subiendo y analizando video...')

    const formData = new FormData()
    formData.append('file', videoSeleccionado)

    try {
      const respuesta = await fetch(
        `${API_BASE_URL}/api/analizar`,
        {
          method: 'POST',
          body: formData,
        }
      )

      const datos = await respuesta.json()

      if (!respuesta.ok) {
        throw new Error(
          datos.detail || 'Error durante el análisis del video.'
        )
      }

      setResultadoVideo(
        `${datos.video?.startsWith('http') ? datos.video : `${API_BASE_URL}${datos.video || ''}`}`
      )

      if (datos.metricas) {
        setMetricasReales({
          jugadores_detectados: Number(
            datos.metricas.jugadores_detectados || 0
          ),
          velocidad_maxima: Number(
            datos.metricas.velocidad_maxima || 0
          ),
          distancia_maxima: Number(
            datos.metricas.distancia_maxima || 0
          ),
          jugadores: Array.isArray(datos.metricas.jugadores)
            ? datos.metricas.jugadores
            : [],
        })
      }

      setMensajeAnalisis('✅ Análisis completado correctamente.')

      // Guardar únicamente el análisis actual.
      setAnalisisActual({
        nombre: nombreAnalisis.trim(),
        fecha: new Date().toLocaleDateString('es-BO'),
        video: datos.video,
        metricas: datos.metricas || {
          jugadores_detectados: 0,
          velocidad_maxima: 0,
          distancia_maxima: 0,
          jugadores: []
        }
      })
    } catch (error) {
      console.error('Error en /api/analizar:', error)
      setMensajeAnalisis(`❌ ${error.message}`)
    } finally {
      setAnalizando(false)
    }
  }

  

  // ==============================
  // ELIMINAR ANÁLISIS ACTUAL
  // ==============================

  const eliminarAnalisis = async () => {
    const confirmar = window.confirm(
      '¿Está seguro de eliminar el análisis actual y sus resultados?'
    )

    if (!confirmar) return

    try {
      await fetch(`${API_BASE_URL}/api/analisis`, {
        method: 'DELETE'
      })
    } catch (error) {
      console.warn('No se pudo eliminar el archivo del servidor:', error)
    }

    setAnalisisActual(null)
    setVideoSeleccionado(null)
    setResultadoVideo(null)
    setMensajeAnalisis('')
    setNombreAnalisis('')
    setMetricasReales({
      jugadores_detectados: 0,
      velocidad_maxima: 0,
      distancia_maxima: 0,
      jugadores: []
    })
    setMostrarSesionForm(false)
  }

  // ==============================
  // NAVEGACIÓN
  // ==============================

  const cambiarPagina = (nuevaPagina) => {
    setPagina(nuevaPagina)
  }

  // ==============================
  // REPORTES
  // ==============================

  const generarReporte = () => {
    const contenido = `
FOOTBALL PERFORMANCE
REPORTE DE ANÁLISIS

Fecha: ${new Date().toLocaleDateString()}

Jugadores detectados en el último análisis: ${metricasReales.jugadores_detectados}

Análisis: ${analisisActual?.nombre || 'Sin análisis activo'}

Fecha del análisis: ${analisisActual?.fecha || 'Sin registro'}

Velocidad máxima real: ${metricasReales.velocidad_maxima.toFixed(2)} km/h

Distancia máxima registrada: ${metricasReales.distancia_maxima.toFixed(2)} m


Sistema de visión artificial: ${visionArtificial}

Sistema de tracking: ${tracking}

Estado de API: ${estadoAPI}

Reporte generado desde Football Performance.
`

    const archivo = new Blob([contenido], {
      type: 'text/plain',
    })

    const url = URL.createObjectURL(archivo)

    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = 'reporte-football-performance.txt'
    enlace.click()

    URL.revokeObjectURL(url)
  }

  // ==============================
  // SIDEBAR
  // ==============================

  const Sidebar = () => (
    <aside className="sidebar">

      <div className="logo">

        <div className="logo-ball">
          ⚽
        </div>

        <div>
          <strong>Football</strong>
          <span>Performance</span>
        </div>

      </div>

      <nav>

        <button
          className={`menu ${
            pagina === 'inicio' ? 'active' : ''
          }`}
          onClick={() => cambiarPagina('inicio')}
        >
          🏠
          <span>Inicio</span>
        </button>

        <button
          className={`menu ${
            pagina === 'jugadores' ? 'active' : ''
          }`}
          onClick={() => cambiarPagina('jugadores')}
        >
          👥
          <span>Jugadores</span>
        </button>

        <button
          className={`menu ${
            pagina === 'sesiones' ? 'active' : ''
          }`}
          onClick={() => cambiarPagina('sesiones')}
        >
          🎥
          <span>Sesiones</span>
        </button>

        <button
          className={`menu ${
            pagina === 'analisis' ? 'active' : ''
          }`}
          onClick={() => cambiarPagina('analisis')}
        >
          📊
          <span>Análisis</span>
        </button>

        <button
          className={`menu ${
            pagina === 'reportes' ? 'active' : ''
          }`}
          onClick={() => cambiarPagina('reportes')}
        >
          📄
          <span>Reportes</span>
        </button>

      </nav>

    </aside>
  )

  // ==============================
  // CABECERA
  // ==============================

  const Header = () => (
    <header className="topbar">

      <div>

        <h1>
          {pagina === 'inicio' && 'Dashboard'}
          {pagina === 'jugadores' && 'Jugadores'}
          {pagina === 'sesiones' && 'Sesiones'}
          {pagina === 'analisis' && 'Análisis'}
          {pagina === 'reportes' && 'Reportes'}
        </h1>

        <p>
          Análisis del rendimiento futbolístico
        </p>

        <div className="api-status">

          <span
            className={
              estadoAPI === 'Sin conexión'
                ? 'api-dot offline'
                : 'api-dot'
            }
          >
            ●
          </span>

          API: {estadoAPI} · {visionArtificial} · {tracking}

        </div>

      </div>



    </header>
  )

  // ==============================
  // INICIO
  // ==============================

  const Inicio = () => (
    <>
      <section className="welcome">

        <div>

          <h2>
            Bienvenido a Football Performance ⚽
          </h2>

          <p>
            Analiza sesiones de entrenamiento mediante
            visión artificial y obtén métricas del
            rendimiento de los jugadores.
          </p>

        </div>

        <button
          className="primary-button"
          onClick={() => cambiarPagina('sesiones')}
        >
          + Nueva sesión
        </button>

      </section>

      <section className="stats">

        <div className="stat-card">

          <span className="stat-icon">
            👥
          </span>

          <div>
            <p>Jugadores detectados</p>
            <h3>{metricasReales.jugadores_detectados}</h3>
          </div>

        </div>

        <div className="stat-card">

          <span className="stat-icon">
            🎥
          </span>

          <div>
            <p>Análisis activo</p>
            <h3>{analisisActual ? 1 : 0}</h3>
          </div>

        </div>

        <div className="stat-card">

          <span className="stat-icon">
            🏃
          </span>

          <div>
            <p>Velocidad máxima</p>

            <h3>
              {metricasReales.velocidad_maxima.toFixed(2)} <small>km/h</small>
            </h3>

          </div>

        </div>

        <div className="stat-card">

          <span className="stat-icon">
            📏
          </span>

          <div>

            <p>Distancia máxima</p>

            <h3>
              {metricasReales.distancia_maxima.toFixed(2)} <small>m</small>
            </h3>

          </div>

        </div>

      </section>

      <section className="content-grid">

        <div className="video-card">

          <div className="card-header">

            <div>

              <h2>
                Último análisis
              </h2>

              <p>
                Partido procesado mediante visión artificial
              </p>

            </div>

            <span className="status">
              ● Procesado
            </span>

          </div>

          <div className="video-container">

            <video
              className="analysis-video"
              controls
              preload="metadata"
            >

              <source
                src={
                  resultadoVideo ||
                  'https://football-performance.onrender.com/resultados/output_video.mp4'
                }
                type="video/mp4"
              />

              Tu navegador no puede reproducir este formato de video.

            </video>

          </div>

        </div>

        <div className="players-card">

          <div className="card-header">

            <div>

              <h2>
                Jugadores destacados
              </h2>

              <p>
                Última sesión
              </p>

            </div>

          </div>

          {metricasReales.jugadores?.length > 0 ? (
            metricasReales.jugadores.slice(0, 3).map((jugador) => (
              <div className="player" key={`destacado-${jugador.id}`}>
                <div className="player-number">
                  {jugador.id}
                </div>

                <div className="player-info">
                  <strong>Jugador #{jugador.id}</strong>
                  <span>Detectado por YOLO</span>
                </div>

                <strong>
                  {Number(jugador.velocidad || 0).toFixed(2)} km/h
                </strong>
              </div>
            ))
          ) : (
            <p style={{ padding: '15px' }}>
              Realice un análisis para mostrar los jugadores detectados.
            </p>
          )}

        </div>

      </section>
    </>
  )

  // ==============================
  // JUGADORES DETECTADOS
  // ==============================

  const Jugadores = () => (
    <section className="page-card">
      <div className="page-header">
        <div>
          <h2>Jugadores detectados</h2>
          <p>
            Resultados obtenidos automáticamente mediante visión artificial.
          </p>
        </div>

        <span className="status">
          ● {metricasReales.jugadores_detectados} detectados
        </span>
      </div>

      {metricasReales.jugadores?.length > 0 ? (
        <div className="table-container">
          <h3 style={{ margin: '15px 0' }}>
            Resultados detectados por visión artificial
          </h3>

          <table>
            <thead>
              <tr>
                <th>ID YOLO</th>
                <th>Jugador detectado</th>
                <th>Velocidad máxima</th>
                <th>Distancia</th>
              </tr>
            </thead>

            <tbody>
              {metricasReales.jugadores.map((jugador) => (
                <tr key={`yolo-${jugador.id}`}>
                  <td><strong>{jugador.id}</strong></td>
                  <td>Jugador #{jugador.id}</td>
                  <td>
                    {Number(jugador.velocidad || 0).toFixed(2)} km/h
                  </td>
                  <td>
                    {Number(jugador.distancia || 0).toFixed(2)} m
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ padding: '30px', textAlign: 'center' }}>
          <h3>No hay jugadores detectados todavía</h3>
          <p>
            Ve a <strong>Sesiones</strong>, selecciona un video y pulsa
            <strong> Analizar video</strong>.
          </p>
        </div>
      )}
    </section>
  )

  // ==============================
  // SESIONES
  // ==============================

  const Sesiones = () => (
    <section className="page-card">

      <div className="page-header">

        <div>

          <h2>
            Análisis de video
          </h2>

          <p>
            Realice un análisis de video a la vez y consulte sus resultados.
          </p>

        </div>

        <button
          className="primary-button"
          onClick={() =>
            setMostrarSesionForm(!mostrarSesionForm)
          }
        >
          + Nueva sesión
        </button>

      </div>

      {analisisActual && !mostrarSesionForm && (
        <div className="form-card" style={{ marginBottom: '20px' }}>
          <h3>📌 Análisis actual</h3>
          <p>
            <strong>{analisisActual.nombre}</strong> · {analisisActual.fecha}
          </p>

          <div className="form-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => cambiarPagina('analisis')}
            >
              📊 Ver análisis
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={() => cambiarPagina('reportes')}
            >
              📄 Ver reporte
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={eliminarAnalisis}
            >
              🗑️ Eliminar
            </button>
          </div>
        </div>
      )}

      {mostrarSesionForm && (

        <div className="form-card">

          <h3>⚽ Nuevo análisis de partido</h3>

          <p>
            Seleccione un video de fútbol para analizarlo
            automáticamente mediante visión artificial.
          </p>

          <div className="form-grid">

            <div>
              <label>Nombre del análisis</label>
              <input
                type="text"
                value={nombreAnalisis}
                onChange={(e) => setNombreAnalisis(e.target.value)}
                placeholder="Ej.: Partido amistoso Sub-20"
              />
            </div>

            <div>
              <label>Video del partido</label>

              <input
                type="file"
                accept="video/mp4,video/avi,video/mov,video/mkv"
                onChange={seleccionarVideo}
              />
            </div>

          </div>

          {videoSeleccionado && (
            <div
              style={{
                marginTop: '20px',
                padding: '15px',
                background: '#f5f7fb',
                borderRadius: '10px'
              }}
            >
              <strong>Video seleccionado:</strong>
              <p>{videoSeleccionado.name}</p>
            </div>
          )}

          {mensajeAnalisis && (
            <div
              style={{
                marginTop: '20px',
                padding: '15px',
                borderRadius: '10px'
              }}
            >
              {mensajeAnalisis}
            </div>
          )}

          <div className="form-actions">

            <button
              type="button"
              className="secondary-button"
              onClick={() => setMostrarSesionForm(false)}
              disabled={analizando}
            >
              Cancelar
            </button>

            <button
              type="button"
              className="primary-button"
              onClick={analizarVideo}
              disabled={analizando}
            >
              {analizando ? '⏳ Analizando...' : '🚀 Analizar video'}
            </button>

          </div>

          {resultadoVideo && (
            <div style={{ marginTop: '20px' }}>
              <h3>✅ Video analizado</h3>

              <video
                className="analysis-video"
                controls
                style={{ width: '100%', marginTop: '10px' }}
                src={resultadoVideo}
              />

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '15px' }}>
                <a
                  href={resultadoVideo}
                  target="_blank"
                  rel="noreferrer"
                  className="primary-button"
                  style={{
                    display: 'inline-block',
                    textDecoration: 'none'
                  }}
                >
                  ▶ Abrir resultado
                </a>

                <button
                  type="button"
                  onClick={descargarVideo}
                  className="primary-button"
                  style={{
                    border: 'none',
                    cursor: 'pointer'
                  }}
                >
                  ⬇️ Descargar video
                </button>
              </div>
            </div>
          )}

        </div>

      )}

      {!analisisActual && !mostrarSesionForm && (
        <div
          className="session-list"
          style={{ padding: '30px', textAlign: 'center' }}
        >
          <h3>No hay un análisis activo</h3>
          <p>
            Pulse <strong>+ Nueva sesión</strong> para seleccionar un video
            y comenzar el análisis.
          </p>
        </div>
      )}

    </section>
  )

  // ==============================
  // ANÁLISIS
  // ==============================

  const Analisis = () => (
    <>

      <section className="page-card">

        <div className="page-header">

          <div>

            <h2>
              Análisis mediante visión artificial
            </h2>

            <p>
              Resultados obtenidos mediante YOLO y ByteTrack.
            </p>

          </div>

          <span className="status">
            ● Sistema activo
          </span>

        </div>

        <div className="analysis-layout">

          <div>

            <video
              className="analysis-video large"
              controls
            >

              <source
                src={
                  resultadoVideo ||
                  'https://football-performance.onrender.com/resultados/output_video.mp4'
                }
                type="video/mp4"
              />

              Tu navegador no puede reproducir este video.

            </video>

          </div>

          <div className="metrics-panel">

            <div className="metric">

              <span>🏃</span>

              <div>
                <small>Velocidad máxima</small>
                <strong>{metricasReales.velocidad_maxima.toFixed(2)} km/h</strong>
              </div>

            </div>

            <div className="metric">

              <span>📏</span>

              <div>
                <small>Distancia estimada</small>
                <strong>{metricasReales.distancia_maxima.toFixed(2)} m</strong>
              </div>

            </div>

            <div className="metric">

              <span>👥</span>

              <div>
                <small>Jugadores detectados</small>
                <strong>{metricasReales.jugadores_detectados}</strong>
              </div>

            </div>

            <div className="metric">

              <span>🤖</span>

              <div>
                <small>Modelo</small>
                <strong>YOLO</strong>
              </div>

            </div>

          </div>

        </div>

      </section>

    </>
  )

  // ==============================
  // REPORTES
  // ==============================

  const Reportes = () => (
    <section className="page-card">

      <div className="page-header">

        <div>

          <h2>
            Reportes
          </h2>

          <p>
            Genere un reporte de los resultados registrados.
          </p>

        </div>

      </div>

      <div className="report-card">

        <div className="report-icon">
          📄
        </div>

        <div>

          <h3>
            Reporte de rendimiento futbolístico
          </h3>

          <p>
            Incluye jugadores, sesiones, velocidad,
            distancia y tecnologías utilizadas.
          </p>

        </div>

        <button
          className="primary-button"
          onClick={generarReporte}
        >
          Descargar reporte
        </button>

      </div>

    </section>
  )

  // ==============================
  // CONFIGURACIÓN
  // ==============================

  const Configuracion = () => (
    <section className="page-card">

      <div className="page-header">

        <div>

          <h2>
            Configuración
          </h2>

          <p>
            Información de la configuración del sistema.
          </p>

        </div>

      </div>

      <div className="settings-list">

        <div className="setting">
          <strong>Backend</strong>
          <span>FastAPI · 127.0.0.1:8000</span>
        </div>

        <div className="setting">
          <strong>Visión artificial</strong>
          <span>{visionArtificial}</span>
        </div>

        <div className="setting">
          <strong>Seguimiento</strong>
          <span>{tracking}</span>
        </div>

        <div className="setting">
          <strong>Frontend</strong>
          <span>React + Vite</span>
        </div>

      </div>

    </section>
  )

  // ==============================
  // RENDER PRINCIPAL
  // ==============================

  return (
    <div className="app">

      <Sidebar />

      <main className="main">

        <Header />

        {pagina === 'inicio' && <Inicio />}

        {pagina === 'jugadores' && <Jugadores />}

        {pagina === 'sesiones' && <Sesiones />}

        {pagina === 'analisis' && <Analisis />}

        {pagina === 'reportes' && <Reportes />}

        {pagina === 'configuracion' && <Configuracion />}

      </main>

    </div>
  )
}

export default App