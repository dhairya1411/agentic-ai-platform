FROM node:22.11.0-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install --ignore-scripts
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22.11.0-alpine
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
RUN addgroup --system --gid 10001 app && adduser --system --uid 10001 --ingroup app app
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/src ./src
COPY --from=build /app/tsconfig.json ./tsconfig.json
RUN chown -R app:app /app
USER app
EXPOSE 3000
CMD ["npm", "run", "start"]
