using System;
using System.IO;
using System.Threading.Tasks;
using KountJwtAuth.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Polly;
using Polly.Extensions.Http;
using Serilog;

namespace ClientDemoApp
{
    internal class Program
    {
        public static async Task Main(string[] args)
        {
            var configuration = new ConfigurationBuilder()
                .SetBasePath(Directory.GetCurrentDirectory())
                .AddEnvironmentVariables()
                .Build();

            Log.Logger = new LoggerConfiguration()
                .WriteTo.File("kount.log", rollingInterval: RollingInterval.Day)
                .CreateLogger();

            try
            {
                Log.Information("Starting application...");

                var host = Host.CreateDefaultBuilder(args)
                    .UseSerilog()
                    .ConfigureServices((context, services) =>
                    {
                        services.AddSingleton<IConfiguration>(configuration);

                        services.AddHttpClient<TokenService>()
                            .AddPolicyHandler(HttpPolicyExtensions
                                .HandleTransientHttpError()
                                .WaitAndRetryAsync(3, retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt))));

                        services.AddSingleton(TokenManager.Instance);
                    })
                    .Build();

                var tokenService = host.Services.GetRequiredService<TokenService>();
                var token = await tokenService.GetValidTokenAsync();

                Log.Information("Retrieved JWT Token: {Token}", token);
                Log.Information("Press Ctrl+C to exit. Token auto-refresh will continue running.");

                await Task.Delay(Timeout.Infinite);
            }
            catch (Exception ex)
            {
                Log.Fatal(ex, "Application terminated unexpectedly");
            }
            finally
            {
                Log.CloseAndFlush();
            }
        }
    }
}