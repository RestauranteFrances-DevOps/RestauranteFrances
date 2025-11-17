# build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

# final stage
FROM node:18-alpine
WORKDIR /app
ENV NODE_ENV=production
# se quiser reduzir tamanho, instale só production no builder e copie node_modules
COPY --from=builder /app ./
EXPOSE 3000
CMD ["node", "server.js"]
