#!/usr/bin/env python3

import argparse
import json
import os
import re
import urllib.parse

import adblock
from publicsuffixlist import PublicSuffixList


class AdblockSimulator:
    def add_filters(self, filters_list, fmt='standard'):
        for filters in filters_list:
            if os.path.isfile(filters):
                if not self.add_filters_from_file(filters, fmt):
                    return False
            elif isinstance(filters, str):
                if not self.add_filters_from_string(filters, fmt):
                    return False
            else:
                return False
        return True

    def add_hosts(self, hosts):
        return self.add_filters(hosts, 'hosts')

    def add_filters_from_file(self, filters_file, fmt='standard'):
        try:
            handle = open(filters_file, 'r')
            filters = handle.read()
            handle.close()
        except Exception:
            return False
        return self.add_filters_from_string(filters, fmt)

    filter_set = None
    engine = None

    def add_filters_from_string(self, filters_string, fmt='standard'):
        try:
            if self.filter_set is None:
                self.filter_set = adblock.FilterSet()
            self.filter_set.add_filter_list(filters_string, fmt)
            self.engine = adblock.Engine(filter_set=self.filter_set)
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
        for dst_urls_list_item in dst_urls_list:
            if os.path.isfile(dst_urls_list_item):
                try:
                    handle = open(dst_urls_list_item, 'r')
                    for line in handle:
                        dst_urls.append(line.strip())
                    handle.close()
                except Exception:
                    return False
            elif isinstance(dst_urls_list_item, str):
                dst_urls.append(dst_urls_list_item)
        results = {}
        for dst_url in sorted(dst_urls, key=self._url_sort_key):
            dst_url = self._prepend_url_scheme(dst_url)
            blocker = self.engine.check_network_urls(
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
        AS.add_filters(args.f)
    if args.h:
        AS.add_hosts(args.h)
    results = AS.simulate(args.s, args.d)
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
