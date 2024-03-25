# Add Royal Render Submission executor to Unreal Engine
import unreal


try:
    settings_class = unreal.MovieRenderPipelineProjectSettings
except AttributeError:
    # Module not available on command line renders
    pass
else:
    import MoviePipelineRoyalSubmit
    
    projectSettings = unreal.get_default_object(settings_class)

    if not projectSettings.default_remote_executor:
        projectSettings.default_remote_executor = MoviePipelineRoyalSubmit.MoviePipelineRoyalSubmit
