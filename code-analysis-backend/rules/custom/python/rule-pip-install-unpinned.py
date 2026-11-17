import os
# ruleid: custom_python_pip-install-unpinned
get_ipython().run_line_magic('pip', 'install -q u8darts pytorch-lightning')
# ruleid: custom_python_pip-install-unpinned
get_ipython().system('pip install requests')
# ruleid: custom_python_pip-install-unpinned
os.system("python -m pip install numpy")
# ok: custom_python_pip-install-unpinned
get_ipython().run_line_magic('pip', 'install -q numpy==1.26.4')
# ok: custom_python_pip-install-unpinned
get_ipython().system('pip install -r requirements.txt')
# ok: custom_python_pip-install-unpinned
get_ipython().run_line_magic('matplotlib', 'inline')
