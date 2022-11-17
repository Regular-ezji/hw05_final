from django.contrib.auth.decorators import login_required
from .utils import paginator
from django.views.decorators.cache import cache_page
from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Group, Follow, User
from .forms import PostForm, CommentForm


@cache_page(20, key_prefix='index_page')
def index(request):
    posts = Post.objects.all()
    template = 'posts/index.html'
    page_obj = paginator(request=request, posts=posts)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    template = 'posts/group_list.html'
    posts = Post.objects.all()
    page_obj = paginator(request=request, posts=posts)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    following = True
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user,
            author=author,
        ).exists
    template = 'posts/profile.html'
    page_obj = paginator(request=request, posts=author.posts.all())
    posts = Post.objects.all().filter(author__username=username)
    count = posts.count()
    context = {
        'page_obj': page_obj,
        'author': author,
        'count': count,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, id=post_id)
    all_posts = Post.objects.all()
    counter = all_posts.count()
    form = CommentForm()
    comments = post.comments.all()
    context = {
        'post': post,
        'counter': counter,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm()
    context = {
        'form': form
    }
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', post.author)
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    posts = Post.objects.select_related('group')
    post = get_object_or_404(posts, id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    context = {
        'form': form,
        'is_edit': True
    }
    if post.author != request.user:
        return redirect('posts:access_denied')
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    return render(request, template, context)


def access_denied(request):
    template = 'posts/access_denied.html'
    return render(request, template)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    print(123)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user).all()
    template = 'posts/follow.html'
    page_obj = paginator(request=request, posts=posts)
    context = {
        'page_obj': page_obj
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    if author == user:
        return redirect('posts:profile', username=username)
    if Follow.objects.filter(author=author).exists():
        return redirect('posts:profile', username=username)
    Follow.objects.create(
        author=author,
        user=user
    )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    Follow.objects.filter(
        user=user,
        author__username=username
    ).delete()
    return redirect('posts:profile', username=username)
