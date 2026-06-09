from src.recognition.detector import AnimalDetector, RawDetection
from src.recognition.api_classifier import APIClassifier, ClassificationResult
from src.recognition.fallback import FallbackClassifier
from src.recognition.feature_extractor import FeatureExtractor
from src.recognition.matcher import IndividualMatcher, MatchResult

__all__ = [
    "AnimalDetector",
    "RawDetection",
    "APIClassifier",
    "ClassificationResult",
    "FallbackClassifier",
    "FeatureExtractor",
    "IndividualMatcher",
    "MatchResult",
]
