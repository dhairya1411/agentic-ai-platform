FROM node:22.11.0-alpine AS dependencies
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev --ignore-scripts

FROM node:22.11.0-alpine
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup --system --gid 10001 app && adduser --system --uid 10001 --ingroup app app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN chown -R app:app /app
USER app
EXPOSE 3000
CMD ["npm", "run", "start"]
