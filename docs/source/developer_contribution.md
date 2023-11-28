# Contributing to ansible-creator

To actively contribute to the development and enhancement of ansible-creator, your participation is valued. Please use pull requests on a branch of your own fork. After [creating your fork on GitHub](https://docs.github.com/en/get-started/quickstart/contributing-to-projects), you can do:

```console
$ git clone --recursive git@github.com:your-name/ansible-creator
$ cd ansible-creator
$ git checkout -b your-branch-name

# DO SOME CODING HERE

$ git add your new files
$ git commit -v
$ git push origin your-branch-name
```

You will then be able to create a pull request from your commit. This will initiate the process of reviewing and merging your contributions.

For contributions affecting core functionality (i.e., anything except docs or examples), ensure to include corresponding tests that validate the changes. Even if you're not providing a code fix, your input is valuable—feel free to raise [issues](https://github.com/ansible/ansible-creator/issues) in the repository.

## Standards

All pull requests undergo automated tests. To ensure that your changes align with project standards, run checks locally before pushing commits using [tox](https://tox.wiki/en/latest/).

## Get in touch

Connect with the ansible-creator community through the [GitHub discussions forum](https://github.com/ansible/ansible-creator/discussions). For real-time interactions, join the `#ansible-devtools` IRC channel on libera.chat or the Matrix room [#devtools:ansible.com](https://matrix.to/#/#devtools:ansible.com). Explore the full list of Ansible IRC and Mailing list options on the Ansible Communication page. Release announcements will be made to the Ansible Announce list. If you encounter security-related concerns, report them via email to [security@ansible.com](mailto:security@ansible.com).

## Code of Conduct

As with all Ansible projects, adhere to the [Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html) to foster a respectful and inclusive collaborative environment. Your contributions, feedback, and engagement are essential to the success of ansible-creator.
