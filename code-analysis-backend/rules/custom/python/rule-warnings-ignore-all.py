import warnings
# ruleid: custom_python_warnings-ignore-all
warnings.filterwarnings("ignore")
# ruleid: custom_python_warnings-ignore-all
warnings.simplefilter("ignore")
# ok: custom_python_warnings-ignore-all
warnings.filterwarnings("ignore", category=DeprecationWarning)
# ok: custom_python_warnings-ignore-all
warnings.filterwarnings("error")
