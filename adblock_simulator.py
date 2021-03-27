#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
import urllib.parse

import adblock
from publicsuffixlist import PublicSuffixList


class AdblockSimulator:
    def add_filter_list(self, filter_list, fmt='standard'):
        for item in filter_list:
            if os.path.isfile(item):
                if not self.add_filter_list_from_file(item, fmt):
                    return False
            elif isinstance(item, str):
                if not self.add_filter_list_from_string(item, fmt):
                    return False
            else:
                return False
        return True

    def add_hosts(self, hosts):
        return self.add_filter_list(hosts, 'hosts')

    def add_filter_list_from_file(self, filter_list_file, fmt='standard'):
        try:
            handle = open(filter_list_file, 'r')
            filter_list_string = handle.read()
            handle.close()
        except Exception:
            return False
        return self.add_filter_list_from_string(filter_list_string, fmt)

    _filter_set = None
    _engine = None

    def add_filter_list_from_string(self, filter_list_string, fmt='standard'):
        try:
            if self._filter_set is None:
                self._filter_set = adblock.FilterSet()
            self._filter_set.add_filter_list(filter_list_string, fmt)
            self._engine = adblock.Engine(filter_set=self._filter_set)
        except Exception:
            return False
        return True

    def _prepend_url_scheme(self, url):
        if not url.startswith('http://') \
                and not url.startswith('https://'):
            url = f'http://{url}'
        return url

    def _get_host(self, url):
        url = self._prepend_url_scheme(url)
        return urllib.parse.urlparse(url).netloc

    _psl = None

    def _get_domain(self, host):
        if self._psl is None:
            self._psl = PublicSuffixList(only_icann=True)
        return self._psl.privatesuffix(host)

    def _url_sort_key(self, url):
        host = self._get_host(url)
        if not host:
            return url
        domain = self._get_domain(host)
        if not domain:
            return host
        return domain

    def simulate(self, src_url, dst_urls_list):
        if os.path.isfile(src_url):
            try:
                handle = open(src_url, 'r')
                src_url = handle.read().strip()
                handle.close()
            except Exception:
                return False
        src_url = self._prepend_url_scheme(src_url)
        dst_urls = []
        for item in dst_urls_list:
            if os.path.isfile(item):
                try:
                    handle = open(item, 'r')
                    for line in handle:
                        dst_urls.append(line.strip())
                    handle.close()
                except Exception:
                    return False
            elif isinstance(item, str):
                dst_urls.append(item)
        results = {}
        for dst_url in sorted(dst_urls, key=self._url_sort_key):
            dst_url = self._prepend_url_scheme(dst_url)
            blocker = self._engine.check_network_urls(
                url=dst_url,
                source_url=src_url,
                request_type='')
            results[dst_url] = not blocker.matched
        return results


if __name__ == '__main__':
    cli = argparse.ArgumentParser(add_help=False)
    cli.add_argument('-f', metavar='FILTERS', action='append')
    cli.add_argument('-h', metavar='HOSTS', action='append')
    cli.add_argument('-s', required=True, metavar='SOURCE')
    cli.add_argument('-d', required=True, metavar='DESTINATION', action='append')
    cli.add_argument('-r', metavar='REGEX')
    cli.add_argument('-j', action='store_true')
    cli.add_argument('-a', action='store_true')
    cli.add_argument('-b', action='store_true')
    args = cli.parse_args()
    if not args.f and not args.h:
        cli.error('one of the following arguments is required: -f, -h')
    AS = AdblockSimulator()
    if args.f:
        if not AS.add_filter_list(args.f):
            print('adding filter list failed')
            sys.exit(1)
    if args.h:
        if not AS.add_hosts(args.h):
            print('adding hosts failed')
            sys.exit(1)
    results = AS.simulate(args.s, args.d)
    if not results:
        print('simulation failed')
        sys.exit(1)
    if args.r:
        for result in results.copy():
            if not re.search(args.r, result):
                del results[result]
    if args.j:
        print(json.dumps(results, indent=4))
    else:
        for dst_url in results:
            if results[dst_url]:
                if args.a:
                    print(dst_url)
                elif not args.b:
                    print(f'\x1b[32;1mALLOW\x1b[0m {dst_url}')
            else:
                if args.b:
                    print(dst_url)
                elif not args.a:
                    print(f'\x1b[31;1mBLOCK\x1b[0m {dst_url}')
