FROM docker.io/library/nginx:stable-alpine

# Semver from frontend/VERSION (independent of backend). Optional BUILD_ID is git SHA.
ARG BUILD_ID=dev

RUN rm -rf /usr/share/nginx/html/*

COPY VERSION /usr/share/nginx/html/VERSION
COPY css /usr/share/nginx/html/css
COPY js /usr/share/nginx/html/js
COPY vendor /usr/share/nginx/html/vendor
COPY configuration /usr/share/nginx/html/configuration
COPY alerts /usr/share/nginx/html/alerts
COPY streaming /usr/share/nginx/html/streaming
COPY help /usr/share/nginx/html/help
COPY app /usr/share/nginx/html/app
COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Bake package version (+ optional build id) for the footer / local fallback.
RUN FRONTEND_VER="$(tr -d '[:space:]' < /usr/share/nginx/html/VERSION)" \
 && printf 'window.HVD_FRONTEND_VERSION = "%s";\nwindow.HVD_BUILD_ID = "%s";\n' \
      "${FRONTEND_VER}" "${BUILD_ID}" \
      > /usr/share/nginx/html/js/version.js

EXPOSE 5482

CMD ["nginx", "-g", "daemon off;"]
