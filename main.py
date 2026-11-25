"""Application entry point for HealthTrack – Personal Health Monitoring System."""

from ui.app import HealthTrackApp


def main() -> None:
    """Launch the HealthTrack desktop GUI."""
    app = HealthTrackApp()
    app.mainloop()


if __name__ == "__main__":
    main()
