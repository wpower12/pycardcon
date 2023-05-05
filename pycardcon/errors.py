class InvalidTextRegion(Exception):
    """ Raised when a text region is missing the required fields to render """
    def __init__(self, text_region, field):
        self.tr = text_region
        self.field = field
        self.message = f"text region '{self.tr}' missing field '{self.field}'."
        self.message += "\n\tcheck that it is being assigned defaults by a frame."
        self.message += "\n\tcheck if you forgot to remove this text region after removing a frame."
        super().__init__(self.message)

