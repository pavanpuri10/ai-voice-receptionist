import os
import pyttsx3

path = os.path.join(os.path.dirname(pyttsx3.__file__), 'drivers', 'nsss.py')
with open(path) as f:
    content = f.read()

if 'import objc\n' not in content:
    content = content.replace(
        'from PyObjCTools.AppHelper import PyObjCAppHelperRunLoopStopper',
        'from PyObjCTools.AppHelper import PyObjCAppHelperRunLoopStopper\nimport objc'
    )
    with open(path, 'w') as f:
        f.write(content)
    print('Patched:', path)
else:
    print('Already has import objc')
