FROM apache/airflow:2.8.1
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         vim \ # Install the vim package
  && apt-get autoremove -yqq --purge \ # Remove packages that were automatically installed to satisfy dependencies for other packages and are no longer needed
  && apt-get clean \ # Remove all packages from the cache
  && rm -rf /var/lib/apt/lists/* # Delete the package lists
  && pip3 install beautifulsoup4 # Install the beautifulsoup4 Python package
USER airflow  # Switch back to the airflow user