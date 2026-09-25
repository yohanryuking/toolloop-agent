# Deploy — toolloop-agent

Guía paso a paso para el Sprint 6 (deploy y presentación). El repo ya está
preparado (`Dockerfile`, `fly.toml`, health check en `/health`); lo que falta
es específico de cada cuenta/servicio y por eso no se puede automatizar desde
acá — hay que ejecutarlo con tus propias credenciales.

Recomendación: **backend en Fly.io** (Docker nativo, soporta volúmenes
persistentes baratos — importante porque usamos SQLite) + **frontend en
Vercel** (build estático de Vite, cero config). Alternativas al final.

## 0. Prerrequisitos

- Cuenta en [Fly.io](https://fly.io) y [Vercel](https://vercel.com).
- `flyctl` instalado (`curl -L https://fly.io/install.sh | sh`) y logueado
  (`fly auth login`).
- Una API key de Anthropic (`ANTHROPIC_API_KEY`). Opcional: `TAVILY_API_KEY`
  si querés que `buscar_web` use resultados reales en vez de mockeados.

## 1. Backend en Fly.io

```bash
cd backend
fly launch --no-deploy   # detecta el Dockerfile, usa fly.toml existente
```

Cuando pregunte por el nombre de la app, poné uno propio (el de `fly.toml`,
`toolloop-agent-api`, ya puede estar tomado por otra cuenta — es un namespace
global de Fly). Si lo cambiás, actualizá `app = "..."` en `backend/fly.toml`.

Crear el volumen para que SQLite persista entre deploys/reinicios:

```bash
fly volumes create toolloop_data --size 1 --region gru
```

(1 GB alcanza de sobra para este proyecto; `--region` debe matchear
`primary_region` en `fly.toml`.)

Configurar los secrets (nunca van en `fly.toml`, que sí se commitea):

```bash
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly secrets set TAVILY_API_KEY=...          # opcional
fly secrets set FRONTEND_ORIGIN=http://localhost:5173   # se corrige en el paso 3
```

Deployar:

```bash
fly deploy
```

Verificar que responde:

```bash
curl https://toolloop-agent-api.fly.dev/health
# {"status":"ok"}
```

Anotá esa URL — la necesitás para el frontend.

## 2. Frontend en Vercel

Desde el dashboard de Vercel: **New Project** → importar este repo → en
"Root Directory" elegir `frontend` (es un monorepo, Vercel necesita saber
que la app está en ese subdirectorio). El framework preset "Vite" se detecta
solo.

Variable de entorno a configurar en el proyecto de Vercel:

- `VITE_API_URL` = `https://toolloop-agent-api.fly.dev` (la URL del backend
  del paso 1, sin `/` al final).

Deployar (botón "Deploy" en el dashboard, o `vercel --prod` con la CLI).
Vercel te da una URL tipo `https://toolloop-agent.vercel.app`.

## 3. Conectar los dos: CORS

El backend solo acepta requests desde el origen configurado en
`FRONTEND_ORIGIN` (`app/main.py`, middleware CORS). Con la URL real del
frontend ya deployado:

```bash
cd backend
fly secrets set FRONTEND_ORIGIN=https://toolloop-agent.vercel.app
```

Esto reinicia la app automáticamente con el secret nuevo. Sin este paso, el
navegador va a bloquear las requests del frontend al backend (error de CORS
en la consola).

## 4. Probar el flujo completo

1. Cargar eventos de ejemplo (una sola vez, contra el backend deployado):
   no hay un endpoint para esto todavía — el script `scripts/seed_events.py`
   asume acceso directo a la base. La forma más simple es correrlo localmente
   apuntando al mismo `DATABASE_URL`, o `fly ssh console` y correrlo dentro
   de la máquina de Fly (`python -m scripts.seed_events`).
2. Abrir el frontend deployado y probar la tarea del brief: *"revisá el
   clima de mañana y si tenemos un evento al aire libre ese día, avisá al
   equipo por email"*.
3. Confirmar en el panel de traza que se ven las tres herramientas
   encadenándose (`buscar_web` → `buscar_eventos` → `enviar_email`).

## Alternativas de hosting

- **Render** en vez de Fly.io: soporta Docker + discos persistentes de forma
  similar (Web Service + "Persistent Disk" apuntando a `/app/data`). Mismo
  `Dockerfile`, no hace falta `fly.toml`.
- **Railway**: similar a Render, con volúmenes también. Bueno si ya tenés
  cuenta ahí del proyecto anterior (Stripe simulado).
- **Netlify** en vez de Vercel para el frontend: mismo concepto (build
  command `npm run build`, publish directory `dist`, variable `VITE_API_URL`).

## Migrar de SQLite a Postgres (opcional)

Solo hace falta si el hosting elegido **no** ofrece disco persistente (varios
free tiers "serverless" lo restringen). Gracias a que todo el acceso a datos
pasa por SQLAlchemy, el cambio es de configuración, no de código:

1. Crear una base Postgres administrada (Neon, Supabase, Railway, RDS, la que
   sea — cualquiera con una connection string estándar sirve).
2. Agregar `asyncpg` a `backend/requirements.txt`.
3. Cambiar `DATABASE_URL` a `postgresql+asyncpg://usuario:pass@host/db`.
4. Redeploy. `init_db()` corre `create_all()` igual que con SQLite.

No hace falta tocar `app/db/models.py` ni ninguna query.

## Checklist final del Sprint 6

- [x] Repo preparado para deploy: `Dockerfile` (con directorio de datos),
      `fly.toml`, health check en `/health`, esta guía.
- [ ] Backend deployado en Fly.io (o alternativa) — requiere cuenta propia.
- [ ] Frontend deployado en Vercel (o alternativa) — requiere cuenta propia.
- [ ] CORS conectado entre ambos (paso 3).
- [ ] Video demo de la tarea multi-paso del brief.
- [x] Post explicando el patrón ReAct — ver [`docs/BLOG_POST.md`](BLOG_POST.md).
