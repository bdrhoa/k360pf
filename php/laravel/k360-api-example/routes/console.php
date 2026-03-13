<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

use Illuminate\Support\Facades\Schedule;

// Run our token fetcher every 15 minutes. 
// If the token is still good, it pulls from cache. 
// If it's near expiry, it automatically reaches out to Kount and gets a new one.
Schedule::command('kount:refresh-token')->everyFifteenMinutes();