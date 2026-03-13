<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Services\KountTokenService;
use Illuminate\Support\Facades\Log;
use Exception;

class RefreshKountToken extends Command
{
    // The console command name/signature
    protected $signature = 'kount:refresh-token {--daemon : Run continuously to test the cache/refresh logic}';

    // The console command description
    protected $description = 'Retrieves a Kount JWT token and tests the KountTokenService';

    /**
     * Execute the console command.
     * Laravel's Service Container automatically injects KountTokenService here.
     */
    public function handle(KountTokenService $tokenService): int
    {
        $this->info("Starting application...");
        Log::channel('kount')->info("Starting application...");

        try {
            // Fetch the token (will hit the API the first time, then use Cache)
            $token = $tokenService->getValidToken();

            $this->info("Retrieved JWT Token: {$token}");
            Log::channel('kount')->info("Retrieved JWT Token: {$token}");

            // If the user runs `php artisan kount:test-token --daemon`
            if ($this->option('daemon')) {
                $this->warn("Press Ctrl+C to exit. Checking token state every 30 seconds.");

                // Keep track of the token we currently have
                $lastKnownToken = $token;
                
                while (true) {
                    sleep(30);
                    
                    // This is lightweight. It just checks the cache unless the 2-minute buffer is hit.
                    // If the buffer is hit, it auto-refreshes seamlessly.
                    $currentToken = $tokenService->getValidToken(); 

                    // If the token changed, print it!
                    if ($currentToken !== $lastKnownToken) {
                        $this->info("\n--- TOKEN REFRESHED ---");
                        $this->info("New JWT Token: {$currentToken}");
                        
                        // Update our tracker
                        $lastKnownToken = $currentToken;
                    }
                    
                    $this->line("Token checked at " . now()->toDateTimeString());
                }
            }

            return Command::SUCCESS;

        } catch (Exception $ex) {
            $this->error("Application terminated unexpectedly: " . $ex->getMessage());
            Log::channel('kount')->critical("Application terminated unexpectedly", ['exception' => $ex]);
            
            return Command::FAILURE;
        }
    }
}