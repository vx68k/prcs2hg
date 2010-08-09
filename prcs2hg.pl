#!/usr/bin/perl

use strict;

my $repository="rglclock";

open(HGLOG, "hg status -X '.$repository.prcs_aux' |") or die "Current directory is not a repository\n";
while (<HGLOG>) {
    die "Directory is not clean\n";
}
close(HGLOG);

my %master = ();
my %created;

open(INFO, "prcs info --sort=date '$repository' |") or die;
while (my $info = <INFO>) {
    my ($version, $deleted) = $info =~ /^$repository ([^ ]+) \S+ by \S+( \*DELETED\*)?$/o;
    print STDERR "version=$version\n";
    next if $deleted ne "";

    my ($branch, $minor) = $version =~ /^(.*)\.(\d+)$/;
    #print STDERR "branch=$branch minor=$minor\n";
    $branch = "prcs-$branch";

    # Switch branches.
    if ($created{$branch}) {
        system("hg update -r '$branch'") == 0 or die;
    } else {
        system("hg branch '$branch'") == 0 or die;
        $created{$branch} = 1;
    }

    system("prcs checkout -f -u -r '$version' '$repository' 2>/dev/null") == 0 or die $!;

    open(PROJECT, "$repository.prj") or die $!;
    undef $/;
    my $project = <PROJECT>;
    $/ = "\n";
    close(PROJECT);
    $project =~ s/\s*;.*$//mg;
    #print STDERR $project;

    my %track = ();

    my ($message) = $project =~ /\(version-log\s+"([^"]*)"\s*\)/i;
    my ($date) = $project =~ /\(checkin-time\s+"([^"]*)"\s*\)/i;
    my ($user) = $project =~ /\(checkin-login\s+([^)\s]*)\s*\)/i;
    #print STDERR "date=$date user=$user\n";

    my ($files) = $project =~ /\(files\s+((?:\s*\([^()]*\([^()]*\)[^()]*\))*)\s*\)/i;
    #print STDERR $files;
    while ($files =~ /\(\s*([^()]*)\s+\(([^()]*)\)(?:\s+([^)]*))?\s*\)/gc) {
        my ($file, $target, $options) = ($1, $2, $3);
        #print STDERR "$file $target $options\n";
        if ($options !~ /:symlink/) {
            $target =~ s/\s.*//;
            $track{$target} = $file;
            system("hg addremove '$file'") == 0 or die;
        }
    }
    system("hg addremove '$repository.prj'") == 0 or die;
    $message = "(no message)" if $message eq "";
    system("hg commit -m '$message' -d '$date' -u '$user'") == 0 or die;

    $master{$branch} = \%track;
}
close(INFO);
