from unittest.mock import Mock

from marge.gitlab import Api, GET, POST, PUT
from marge.merge_request import MergeRequest

_INFO = {
    'id': 42,
    'iid': 54,
    'title': 'a title',
    'project_id': 1234,
    'assignee': {'id': 77},
    'author': {'id': 88},
    'state': 'opened',
    'sha': 'dead4g00d',
    'source_project_id': 5678,
    'target_project_id': 1234,
    'source_branch': 'useless_new_feature',
    'target_branch': 'master',
}


class TestMergeRequest(object):
    def setup_method(self, _method):
        self.api = Mock(Api)
        self.mr = MergeRequest(api=self.api, info=_INFO)

    def test_fetch_by_id(self):
        api = self.api
        api.call = Mock(return_value=_INFO)

        merge_request = MergeRequest.fetch_by_id(project_id=1234, merge_request_id=42, api=api)

        api.call.assert_called_once_with(GET('/projects/1234/merge_requests/42'))
        assert merge_request.info == _INFO

    def test_refetch_info(self):
        new_info = dict(_INFO, state='closed')
        self.api.call = Mock(return_value=new_info)

        self.mr.refetch_info()
        self.api.call.assert_called_once_with(GET('/projects/1234/merge_requests/42'))
        assert self.mr.info == new_info

    def test_properties(self):
        mr = self.mr

        assert mr.id == 42
        assert mr.project_id == 1234
        assert mr.iid == 54
        assert mr.title == 'a title'
        assert mr.assignee_id == 77
        assert mr.author_id == 88
        assert mr.state == 'opened'
        assert mr.source_branch == 'useless_new_feature'
        assert mr.target_branch == 'master'
        assert mr.sha == 'dead4g00d'
        assert mr.source_project_id == 5678
        assert mr.target_project_id == 1234

        self._load({'assignee': {}})
        assert mr.assignee_id == None

    def test_comment(self):
        self.mr.comment('blah')
        self.api.call.assert_called_once_with(POST('/projects/1234/merge_requests/42/notes', {'body': 'blah'}))

    def test_assign(self):
        self.mr.assign_to(42)
        self.api.call.assert_called_once_with(PUT('/projects/1234/merge_requests/42', {'assignee_id': 42}))

    def test_unassign(self):
        self.mr.unassign()
        self.api.call.assert_called_once_with(PUT('/projects/1234/merge_requests/42', {'assignee_id': None}))

    def test_accept(self):
        self._load(dict(_INFO, sha='badc0de'))

        for b in (True, False):
            self.mr.accept(remove_branch=b)
            self.api.call.assert_called_once_with(PUT(
                '/projects/1234/merge_requests/42/merge',
                dict(
                    merge_when_build_succeeds=True,
                    should_remove_source_branch=b,
                    sha='badc0de',
                )
            ))
            self.api.call.reset_mock()

        self.mr.accept(sha='g00dc0de')
        self.api.call.assert_called_once_with(PUT(
            '/projects/1234/merge_requests/42/merge',
            dict(
                merge_when_build_succeeds=True,
                should_remove_source_branch=False,
                sha='g00dc0de',
            )
        ))

    def test_fetch_all_opened(self):
        mr1, mr2 = _INFO, dict(_INFO, id=678)

        api = self.api
        api.collect_all_pages = Mock(return_value = [mr1, mr2])

        result = MergeRequest.fetch_all_opened(1234, api)
        api.collect_all_pages.assert_called_once_with(GET(
            '/projects/1234/merge_requests',
            {'state': 'opened', 'order_by': 'created_at', 'sort': 'asc'},
        ))
        assert [mr.info for mr in result] == [mr1, mr2]

    def _load(self, json):
        old_mock = self.api.call
        self.api.call = Mock(return_value=json)
        self.mr.refetch_info()
        self.api.call.assert_called_with(GET('/projects/1234/merge_requests/42'))
        self.api.call = old_mock