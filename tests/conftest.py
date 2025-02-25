from hypothesis import settings, Phase

settings.register_profile(
    "failfast", phases=[Phase.explicit, Phase.reuse, Phase.generate]
)
