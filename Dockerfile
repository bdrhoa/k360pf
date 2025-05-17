# Use .NET 8.0 SDK for build
FROM mcr.microsoft.com/dotnet/sdk:8.0.408 AS build
WORKDIR /k360

# Copy source code
COPY . /k360

# Restore and publish the app
WORKDIR /k360/dotnet/KountWebhook
RUN dotnet restore KountWebhook.csproj
RUN dotnet publish KountWebhook.csproj -c Release -o /app

# Use runtime-only image
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
COPY --from=build /app .

# Expose port 8000 to Railway
ENV ASPNETCORE_URLS=http://+:8000
EXPOSE 8000

ENTRYPOINT ["dotnet", "KountWebhook.dll"]