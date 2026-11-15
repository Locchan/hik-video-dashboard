FROM docker.io/library/nginx:stable-alpine

RUN rm -rf /usr/share/nginx/html/*

COPY css /usr/share/nginx/html/css
COPY js /usr/share/nginx/html/js
COPY configuration /usr/share/nginx/html/configuration
COPY alerts /usr/share/nginx/html/alerts
COPY app /usr/share/nginx/html/app
COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5482

CMD ["nginx", "-g", "daemon off;"]
