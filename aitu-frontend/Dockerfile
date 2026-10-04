# syntax=docker/dockerfile:1
#
# aitu-frontend, development image (implementation 08, Phase 3; plan section 10.3, Q-5).
#
# It runs the Vite development server with hot reload. `compose.yaml` mounts this folder over
# /work/aimpromptu/aitu-frontend, so an edit on the host reloads the page, and keeps the image's own
# node_modules (built here, for this image) in front of the host's.
#
# The piano sheet package `@aimpromptu/grid-notation` is the sibling repository `vexflow-v2`
# (`file:../../vexflow-v2` in package.json). It reaches the build as the named context `vexflow`
# (compose.yaml, `additional_contexts`) and is built here, at the same relative place as on the
# host, so the `file:` link resolves unchanged. A change in vexflow-v2 needs `make build`.

FROM node:22-bookworm-slim

# The host user's id, so a file Vite or npm writes into the mounted folder belongs to the host user.
ARG UID=1000
ARG GID=1000
RUN if [ "${UID}" != "1000" ]; then \
        groupmod --gid "${GID}" node && usermod --uid "${UID}" --gid "${GID}" node; \
    fi \
    && install -d -o node -g node /work/vexflow-v2 /work/aimpromptu/aitu-frontend
USER node

# 1. vexflow-v2: its packages, then its dist/ (what the frontend imports).
WORKDIR /work/vexflow-v2
COPY --from=vexflow --chown=node:node package.json package-lock.json ./
RUN --mount=type=cache,target=/home/node/.npm,uid=${UID},gid=${GID} npm ci --no-audit --no-fund
COPY --from=vexflow --chown=node:node tsconfig.json tsup.config.ts vitest.config.ts ./
COPY --from=vexflow --chown=node:node src ./src
COPY --from=vexflow --chown=node:node tests ./tests
RUN npm run build

# 2. The frontend's packages. The source is mounted at run time.
WORKDIR /work/aimpromptu/aitu-frontend
COPY --chown=node:node package.json package-lock.json ./
RUN --mount=type=cache,target=/home/node/.npm,uid=${UID},gid=${GID} npm ci --no-audit --no-fund

# Where Vite sends /api (vite.config.ts). compose.yaml points it at the backend service.
ENV AITU_API_PROXY=http://backend:8765
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
