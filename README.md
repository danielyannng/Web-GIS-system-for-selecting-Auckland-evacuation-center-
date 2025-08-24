# Evacuation Center Site Selection — Decision Support System

A Web-GIS decision support system for selecting evacuation center locations (Auckland-focused test dataset). This repository contains a Streamlit web front-end, MCDA-based analysis modules, GeoServer integration for map services, and PostgreSQL/PostGIS data management scripts.

---

## Contents of this README

- Project summary and motivation
- Key features
- Architecture and file structure
- Quick start (local, Docker-assisted)
- Data and data import
- How to use the application (main flows)
- Design and implementation decisions (rationale + references)
- Testing, deployment and troubleshooting
- License and contact

---

## Project summary

Natural hazards require fast, evidence-based decisions about where to locate evacuation centers. This project builds a reproducible pipeline that:

- Ingests multi-source spatial data (census, facilities, roads, hazard zones)
- Publishes spatial layers via GeoServer (WMS/WFS)
- Computes Multi-Criteria Decision Analysis (MCDA) scores for candidate sites
- Presents interactive results through a Streamlit UI with mapping and export features

The system is intended as a research / pilot tool for emergency planners and students; it demonstrates the full geospatial product lifecycle: requirements, design, implementation, testing and deployment.

---

## Key features

- MCDA-based site evaluation with adjustable criteria weights
- Interactive map visualisation (Folium + Leaflet WMS) and WMS layer controls
- Data management: CSV upload, data preview, import scripts for PostGIS
- GeoServer automation utilities for publishing layers
- Export of evaluation results to CSV
- Container-friendly scripts for GeoServer and PostgreSQL

---

## Architecture

High-level components:

1. Streamlit front-end (`app.py` / `app_simple.py`)
2. Analysis components (`src/components/decision_analyzer.py`, `src/components/decision_map.py`)
3. Utilities (`src/utils/geoserver_manager.py`, `src/utils/data_generator.py`)
4. Data folder with sample CSVs and QGIS shapefiles (`data/`)
5. Deployment and maintenance scripts (`scripts/`)

Core services and endpoints (local defaults):

- Streamlit app: `http://localhost:8501`
- GeoServer (admin console): `http://localhost:8080/geoserver/web`
- GeoServer WMS endpoint example: `http://localhost:8080/geoserver/<workspace>/wms`
- PostgreSQL: `localhost:5432` (when using docker)

Default credentials (from `config.py`) — change these for production:

- GeoServer: `admin` / `geoserver`
- Postgres: `postgres` / `postgres`

---

## File tree (selected)

```
streamlit-app/
├── app_simple.py              # Streamlit main app
├── run_app.py                 # Starter / helper
├── config.py                  # Project configuration and default credentials
├── requirements.txt           # Python dependencies
├── data/                      # Example CSVs & QGIS Shapefiles
├── scripts/
│   ├── deploy.py
│   ├── docker-compose-geoserver.yml
│   ├── import_data_to_postgres.py
│   ├── import_qgis_to_postgres.py
│   └── publish_to_geoserver.py
└── src/
    ├── components/            # Decision analyzer, map builders, leaflet-wms
    └── utils/                 # GeoServer manager, data helpers
```

---

## Quick start — Local (recommended for development)

Prerequisites:

- Python 3.8+
- pip
- Docker and Docker Compose (if running GeoServer / Postgres in containers)

1. Install Python dependencies

```bash
pip install -r requirements.txt
```

2. Start PostgreSQL and GeoServer (recommended: run GeoServer and Postgres via Docker). From `scripts/`:

```bash
cd scripts
docker-compose -f docker-compose-geoserver.yml up -d
```

3. Import data into PostGIS (after DB is up):

```bash
python scripts/import_data_to_postgres.py
python scripts/import_qgis_to_postgres.py
python scripts/verify_database.py
```

4. Publish layers to GeoServer (automated script):

```bash
python scripts/publish_to_geoserver.py
```

5. Run Streamlit app

```bash
streamlit run app_simple.py --server.port=8501
```

Open `http://localhost:8501` in your browser.

Notes:
- If you prefer to run a local Postgres install instead of Docker, update `config.py` or export environment variables (`POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).

---

## Quick start — Docker bundle for OS-agnostic deployment

This project includes `scripts/docker-compose-geoserver.yml` to launch GeoServer + Postgres. A minimal container workflow:

```bash
# from repository root
cd scripts
docker-compose -f docker-compose-geoserver.yml up -d
```

Then follow steps 3–5 above to import data, publish layers, and run the app locally. For full system packaging (exporting container images, saving volumes), see Troubleshooting & Packaging.

---

## Data and data import

- Example CSVs are in `data/` (e.g. `auckland_facilities_data_real.csv`, `auckland_population_data_real.csv`).
- QGIS shapefiles are under `data/QGIS Data/`.
- `scripts/import_data_to_postgres.py` and `scripts/import_qgis_to_postgres.py` handle ingestion to PostGIS

Data processing steps performed by the scripts:

1. Basic validation (header presence, minimal row counts)
2. Coordinate reference checks and re-projection if needed
3. Geometry construction for point/line/polygon features
4. Index creation (spatial index) and essential constraints

---

## How to use the application (user flows)

1. Overview tab — high-level project information and system health (GeoServer connection, number of layers)
2. Site evaluation tab — select facility dataset, configure MCDA weights (population, accessibility, risk, capacity, service coverage), run evaluation, view ranked results and statistics
3. Decision map tab — visualise evaluated sites, risk layers and compare top-N scenarios on the map; click markers for details
4. WMS layers tab — choose background maps from GeoServer, adjust transparency, use Leaflet controls for smooth rendering
5. Data management tab — upload CSV, preview, and export results

Export: evaluation results can be downloaded as CSV for offline use.

---

## Design & implementation decisions (rationale)

This section summarises why key choices were made and points to supporting literature.

### MCDA for site selection

Reason: Selecting evacuation centers requires weighing multiple, often conflicting criteria (demand, accessibility, safety, capacity). MCDA is a well-established approach in spatial decision support (Malczewski, 1999; Eastman, 1999).

- Malczewski, J. (1999). GIS and Multicriteria Decision Analysis. Wiley.
- Eastman, J.R. (1999). Multi-criteria evaluation and GIS. In: Geographical Information Systems.

Why included: MCDA allows decision-makers to set weights and explore sensitivity; it is transparent and interpretable — important for emergency planning stakeholders.

### Use of PostGIS + GeoServer

Reason: PostGIS is the standard for scalable spatial databases and supports complex spatial queries. GeoServer exposes OGC-standard WMS/WFS services enabling interoperable map services consumed by the front end.

- PostGIS is proven in production for spatial queries and indexing (Obe & Hsu, 2015).
- GeoServer supports styles (SLD), WMS/WFS and REST automation needed for reproducible publishing.

This stack ensures the project can scale from prototype to operational deployment.

### Streamlit for UI

Reason: Streamlit accelerates building interactive data-driven UI with minimal frontend code. It is ideal for rapid prototyping and for a user base of analysts/planners.

Trade-offs: Not as polished as a full SPA (React/Vue) but faster to develop and iterate, and easily integrated with Python analysis code.

### Leaflet WMS rendering

Reason: Leaflet-based WMS controls reduce flicker and improve UX for dynamic layer selection (compared with reloading entire Folium maps). The `leaflet_wms` component is used to embed smoother WMS layer interactions.

---

## Security and configuration notes

- Default credentials in `config.py` are for development only — change before any shared deployment.
- Avoid exposing GeoServer admin or Postgres directly to public networks without strong authentication and network controls.
- Consider using Docker secrets, vault, or environment-based overrides for production credentials.

---

## Testing and validation

- Unit tests are recommended for `src/components/decision_analyzer.py` and key data utility functions. (Not included by default.)
- Use `scripts/verify_database.py` to confirm tables and spatial indexes exist after import.
- Manual integration tests: run the app, change MCDA weights and verify rankings change consistently; test WMS layer toggles and map interactions.

---

## Packaging & distribution

Two options:

1. GitHub + Docker-compose: Push repository to GitHub and provide `scripts/docker-compose-geoserver.yml`. Users clone and run `docker-compose up`.
2. Full image export: Build images for GeoServer and Postgres, save with `docker save`, and bundle repository + tar of images and data volumes. (See `scripts/deploy.py` as a starting point.)

---

## Troubleshooting

- GeoServer not reachable: `docker ps` → check container; `docker-compose -f scripts/docker-compose-geoserver.yml logs` for errors.
- Postgres connection refused: confirm port mapping and that DB has initialized; check `scripts/import_data_to_postgres.py` error output.
- Streamlit errors: ensure Python deps installed; check `requirements.txt`.

---

## Evidence & evaluation against project goals

The system was designed to meet these goals:

- Evidence-based decision support (MCDA) — implemented and exposed via UI with adjustable weights.
- Spatial context via WMS/WFS (GeoServer) — implemented and automatable via `publish_to_geoserver.py`.
- Reproducible data pipeline — import scripts + configuration are included.

Each design choice is supported by practical considerations (scalability, interoperability, developer productivity) and literature cited above.

---

## References

- Malczewski, J. (1999). GIS and Multicriteria Decision Analysis. Wiley.
- Eastman, J.R. (1999). Multi-criteria evaluation and GIS. In: Geographical Information Systems.
- Obe, R. & Hsu, L. (2015). PostGIS in Action. Manning.

---

## License

This repository is for academic / research use. See `LICENSE` for details (if present). If you need an explicit license, add one (MIT or similar).

---

## Contact

For questions or help running the system, open an issue or contact the repository owner.


---
