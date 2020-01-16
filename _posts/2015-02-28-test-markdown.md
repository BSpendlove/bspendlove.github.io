---
layout: post
title: Test markdown
subtitle: Each post also has a subtitle
gh-repo: daattali/beautiful-jekyll
gh-badge: [star, fork, follow]
tags: [test]
comments: true
---

You can write regular [markdown](http://markdowntutorial.com/) here and Jekyll will automatically convert it to a nice webpage.  I strongly encourage you to [take 5 minutes to learn how to write in markdown](http://markdowntutorial.com/) - it'll teach you how to transform regular text into bold/italics/headings/tables/etc.

{% highlight python linenos %}
from netmiko import ConnectHandler
from flask import render_template
from app import app

@app.route('/')
@app.route('/index')
def index():
    user = {'username': 'testUser'}
    device = getInfo()
    return render_template('index.html', title='Home', user=user, device=device)

def getInfo():
    return({'ip':'1.2.3.4', 'hostname' : 'RTR01'})
{% endhighlight %}

