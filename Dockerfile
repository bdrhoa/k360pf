# Use .NET 7.0 SDK for build
FROM mcr.microsoft.com/dotnet/sdk:7.0 AS build
WORKDIR /src

# Copy source code
COPY . .

# Restore and publish the app
WORKDIR /src/k360/dotnet/KountWebhook
RUN dotnet restore KountWebhook.csproj
RUN dotnet publish KountWebhook.csproj -c Release -o /app

# Use runtime-only image
FROM mcr.microsoft.com/dotnet/aspnet:7.0 AS runtime
WORKDIR /app
COPY --from=build /app .

# Expose port 8000 to Railway
ENV ASPNETCORE_URLS=http://+:8000
EXPOSE 8000

ENTRYPOINT ["dotnet", "KountWebhook.dll"]