class ToolSense:
    READ = "read"
    WRITE = "write"

    @classmethod
    def list(cls):
        return [
            getattr(cls, attr) for attr in vars(cls)
            if not attr.startswith("__") and isinstance(getattr(cls, attr), str)
        ]
