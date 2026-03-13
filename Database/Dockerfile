FROM postgres:16-alpine

# Bundle initialization SQL into the image so compose works from host and devcontainer.
COPY init.sql /docker-entrypoint-initdb.d/init.sql
