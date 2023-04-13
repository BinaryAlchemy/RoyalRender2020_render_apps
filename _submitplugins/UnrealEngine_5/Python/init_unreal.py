# Add Royal Render Submission executor to Unreal Engine
import unreal
import MoviePipelineRoyalSubmit


projectSettings = unreal.get_default_object(unreal.MovieRenderPipelineProjectSettings)
if not projectSettings.default_remote_executor:
    projectSettings.default_remote_executor = MoviePipelineRoyalSubmit.MoviePipelineRoyalSubmit
