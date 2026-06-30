# 404gen-color-primitives

Open-source 404-GEN subnet 17 miner for Competition 2.

This miner converts the prompt image into a low-poly Three.js object by extracting
dominant colors, coarse symmetry, edge density, and aspect cues. It emits one
standalone ES module per prompt, each exporting `generate(THREE)`.

## API

The Docker service implements the required batch API:

- `GET /health`
- `GET /status`
- `POST /generate`
- `GET /results`

## Run

```bash
docker build -f docker/Dockerfile -t 404gen-color-primitives .
docker run --rm -p 10006:10006 404gen-color-primitives
```

## Verify

```bash
python3 -m py_compile miner_service.py generator.py verify_local.py
python3 verify_local.py
```
