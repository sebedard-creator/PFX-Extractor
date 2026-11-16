"""Targeted human shouting/screaming activity, embedded in Bandit V4.1."""


def _screaming_activity(scores):
    if DUCK_DEPTH_CRIS <= 0:
        return np.zeros(scores.shape[0], dtype=np.float32)
    return _soft_threshold(
        _max_class_score(scores, SCREAM_CLASS_IDX), *YAMNET_THRESHOLDS['screaming']
    )


def _screaming_frames(scores):
    # Same short temporal margin as the existing targeted human masks.
    return _attack_release_frames(
        _neighbor_peak_frames(_screaming_activity(scores)), attack_s=0.05, release_s=0.65
    )
