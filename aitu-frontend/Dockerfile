# syntax=docker/dockerfile:1
#
# aitu-frontend, development image (implementation 08, Phase 3; plan section 10.3, Q-5).
#
# It runs the Vite development server with hot reload. `compose.yaml` mounts this folder over
# /work/aimpromptu/aitu-frontend, so an edit on the host reloads the page, and keeps the image's own
# node_modules (built here, for this image) in front of the host's.
#
# The piano sheet is drawn by the backend (implementation 03). The vexflow-v2 package that drew it
# here before (`@aimpromptu/grid-notation`, the sibling repository) was removed in implementation 03,
# Phase 10, with the step that built it into this image.

FROM node:22-bookworm-slim

# The host user's id, so a file Vite or npm writes into the mounted folder belongs to the host user.
ARG UID=1000
ARG GID=1000
RUN if [ "${UID}" != "1000" ]; then \
        groupmod --gid "${GID}" node && usermod --uid "${UID}" --gid "${GID}" node; \
    fi \
    && install -d -o node -g node /work/aimpromptu/aitu-frontend
USER node

# The frontend's packages. The source is mounted at run time.
WORKDIR /work/aimpromptu/aitu-frontend
COPY --chown=node:node package.json package-lock.json ./
RUN --mount=type=cache,target=/home/node/.npm,uid=${UID},gid=${GID} npm ci --no-audit --no-fund

# Where Vite sends /api (vite.config.ts). compose.yaml points it at the backend service.
ENV AITU_API_PROXY=http://backend:8765
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
