from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    generator = (root / "generator.py").read_text(encoding="utf-8")
    service = (root / "miner_service.py").read_text(encoding="utf-8")
    dockerfile = (root / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert "export default function generate(THREE)" in generator
    assert "Math.random" not in generator
    assert "Date" not in generator
    assert "color_variance" in generator
    assert "warm_bias" in generator
    assert "foreground_ratio" in generator
    assert "foot_z" in generator
    assert "cap_rounding" in generator
    assert "batch_size" in service
    assert "@app.get(\"/health\")" in service
    assert "@app.get(\"/status\")" in service
    assert "@app.post(\"/generate\")" in service
    assert "@app.get(\"/results\")" in service
    assert "prompts must not be empty" in service
    assert "EXPOSE 10006" in dockerfile
    print("ok")


if __name__ == "__main__":
    main()
