from rise_eo.bands import modify
from rise_eo.model.adapter import BaseModelAdapter

class CropRFS1(BaseModelAdapter):
    required_bands = ["vv", "vh"]          # raw bands SEQ consumes
    n_timestamps = 0                       # set per-instance at bundle time
    output_dtype = "uint8"
    output_nodata = 255
    output_band_names = ["crop_class"]
    feature_sequence = [
        (modify.mask_invalid_and_interpolate, {}),
    ]

    def load(self):
        import joblib
        self.clf, self.le = joblib.load(self.artifacts["model"])

    def predict(self, X_chunk):
        return self.clf.predict(X_chunk).astype("uint8")
