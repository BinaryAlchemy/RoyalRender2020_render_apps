# Add Royal Render Submission executor to Unreal Engine
import unreal


try:
    settings_class = unreal.MovieRenderPipelineProjectSettings
except AttributeError:
    # Module not available on command line renders
    pass
else:
    from MoviePipelineRoyalSubmit import MoviePipelineRoyalSubmit

    try:
        from init_unreal__inhouse import *
    except ModuleNotFoundError:
        # No inhouse init module
        pass
