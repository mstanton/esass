from esass.probes.config import initialize_system


def verify():
    print("Initializing ESASS system...")
    registry, pipeline, config = initialize_system()

    probe_names = [p.name for p in registry.probes]
    print(f"Registered probes: {probe_names}")

    if "ReliabilityProbe" in probe_names:
        print("✅ ReliabilityProbe found")
    else:
        print("❌ ReliabilityProbe NOT found")

    if "FieldBoundaryProbe" in probe_names:
        print("✅ FieldBoundaryProbe found")
    else:
        print("❌ FieldBoundaryProbe NOT found")


if __name__ == "__main__":
    verify()
