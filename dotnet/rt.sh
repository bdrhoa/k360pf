#!/bin/bash

# Run tests and generate HTML report
dotnet test --logger "html;LogFileName=test-results.html"

