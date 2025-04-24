# Add Royal Render Submission executor to Unreal Engine
import unreal


try:
    settings_class = unreal.MovieRenderPipelineProjectSettings
except AttributeError:
    # Module not available on command line renders
    pass
else:
    import MoviePipelineRoyalSubmit


def set_royal_executor():
    """Set remote executor to RoyalSubmit if not set to anything.
    WARNING: might corrupt DefaultEngine.ini by resolving to full path on later versions"""
    projectSettings = unreal.get_default_object(settings_class)

    if not projectSettings.default_remote_executor:
        projectSettings.default_remote_executor = MoviePipelineRoyalSubmit.MoviePipelineRoyalSubmit
