// Program.cs
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
            
            var apiKey = configuration["KOUNT_API_KEY"];
            if (string.IsNullOrEmpty(apiKey))
            {
                Console.WriteLine("Warning: KOUNT_API_KEY environment variable is not set.");
            }
            else
            {
                Console.WriteLine("KOUNT_API_KEY successfully loaded.");
            }
            var host = Host.CreateDefaultBuilder(args)

                .ConfigureServices((context, services) =>
                {
                    services.AddSingleton<IConfiguration>(configuration);

                    services.AddLogging(configure => configure.AddConsole());

                    services.AddHttpClient<TokenService>()
                        .AddPolicyHandler(HttpPolicyExtensions
                            .HandleTransientHttpError()
                            .WaitAndRetryAsync(3, retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt))));

                    services.AddSingleton(TokenManager.Instance);
                })
                .Build();

            var tokenService = host.Services.GetRequiredService<TokenService>();
            var token = await tokenService.GetValidTokenAsync();

            Console.WriteLine("Retrieved JWT Token:");
            Console.WriteLine(token);

            Console.WriteLine("Press Ctrl+C to exit. Token auto-refresh will continue to run in the background.");
            await Task.Delay(Timeout.Infinite);
        }
    }
}
