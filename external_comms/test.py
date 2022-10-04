import difflib


def check(str_a, str_b):
    print('{} => {}'.format(str_a, str_b))
    for i, s in enumerate(difflib.ndiff(str_a, str_b)):
        if s[0] == ' ':
            continue
        elif s[0] == '-':
            print(u'Delete "{}" from position {}'.format(s[-1], i))
        elif s[0] == '+':
            print(u'Add "{}" to position {}'.format(s[-1], i))
    print()


check("qEe+qZUETTZ1+RO5DJnLT6n1g/wrhR2SIlBjP1/eLjg79hVmtzyZFaU1Pm8FmRfwrgwb9X0uhZyZ9xt7iqmfh8w/3kNIghd5jaQArJGV+0i2NMEypwkdWhN8GlvjVYMB8Soed4P68CDCgjsPEdJhttd7tgVujJMCxHf6HPdenq6MZV2Qn+RW+u+7NyI6RSxFG61OtRTKr59ah3PDvgrgJDwHou19JQWvLPawACok1wVfMlAUJguWfeaCZ820i5Xmx23zgiddi8uT+eTyyJD7pxcP58HtDfVPS1SgGJNEi2tbE18zmSrOuiGsfraUAqAZ84Q5H9bFYjdHMboxsnr3RDc7sUs0Tq8yayN6p36uIsFoYemB19p91CEknnIW57I52euOwnrfu8SlYGsAWgqZlg==", "qEe+qZUETTZ1+RO5DJnLT6n1g/wrhR2SIlBjP1/eLjg79hVmtzyZFaU1Pm8FmRfwrgwb9X0uhZyZ9xt7iqmfh8w/3kNIghd5jaQArJGV+0i2NMEypwkdWhN8GlvjVYMB8Soed4P68CDCgjsPEdJhttd7tgVujJMCxHf6HPdenq6MZV2Qn+RW+u+7NyI6RSxFG61OtRTKr59ah3PDvgrgJDwHou19JQWvLPawACok1wVfMlAUJguWfeaCZ820i5Xmx23zgiddi8uT+eTyyJD7")