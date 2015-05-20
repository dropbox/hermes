# Introduction #

Hermes logs events, generates tasks, and tracks tasks in logical groups.

# Terminology #

Rather than mimic the overloaded and overused terminology typically used, and in keeping with the Dropbox principal of "cupcake," Hermes adopts a more interesting language.

## Events and Event Types ##

Events double as journal entries, logging system activities like server restarts, and requests for action, such as a need to restart or turn off a server.

As journal entries, events provide an audit trail and can potentially be used to track a range of activities.  As request entries, events can initialize labors and subsequent events would close these labors.

Each event must be of a predefined event type.  An event type consists of a category and state, the combination of which provides meaningful grouping and definition:

    ID  CATEGORY            STATE
    [1] system-reboot       required
    [2] system-reboot       completed
    [3] system-maintenance  required
    [4] system-maintenance  ready
    [5] system-maintenance  completed

Event types are often written simply as `category-state`, such as `system-reboot-required`.

An individual event entry consists of the event type, the host, and the time of occurrence.

## Labors ##

Labors represent tasks that need to be performed or outstanding issues that need to be addressed for a host.  All labors are created and closed as the result of events.

Labors are usually referred to by the event which triggered its creation, so a `system-reboot-required` event creates a `system-reboot-required` labor.

## Fates ##
### Basics ###
The fates define how labors are created and completed.  A typical fate will specify which event type will result in the creation of a labor for the host, and which event type will close labors for a host.

    [1] system-reboot-required => system-reboot-completed

### Chained Fates ###
An `intermediate` flag in the definition of a fate indicates if the fate only applies to existing labors.  This allows fates to be chained together to essentially create a workflow engine.

For example:
    [1] system-maintenance-required => system-maintenance-ready
    [2] system-maintenance-ready => system-maintenance-completed

(with the second fate being flagged as an intermediate) would essentially mean:

    system-maintenance-required => system-maintenance-ready => system-maintenance-completed

In this example, an event of type `system-maintenance-ready` only creates a labor if an existing labor created by an event of type `system-maintenance-required` was present.

### Choose Your Own Adventure ###

Fates can allow multiple ways to resolve a labor.

    [1] puppet-restart-required => puppet-restart-completed
    [2] puppet-restart-required => system-restart-completed

In this example, a labor created by the event `puppet-restart-required` can be completed by either a `puppet-restart-completed` event, or a `system-restart-completed` event.

## Quests ##

Quests are collections of labors, making tracking and reporting of progress much easier.

For example, when a security fix is released that requires all web servers to be restarted, a quest can be created with a `system-restart-required` labor for all the hosts.

Quests will eventually contain information to outside references, such as Jira tickets.

# Status #

Development is in the early phases.  The first production roll-out of Hermes will offer:

    * **Hermes server:** a central server, run by SysEng, with a REST API
    * **Hermes CLI:** a command line interface to the Hermes server available on any and all necessary servers

Development can be tracked at [GitHub](https://github.com/dropbox/hermes)
and [Travis CI](https://travis-ci.org/dropbox/herme)

# REST API #

## Versioning ##

At the root of all REST URLs is the version.  So you will notice that the
base URL is is `/api/v1/`.

## Limits ##

For any GETs that could potentially return large datasets, a limit can be
explicitly set using the limit parameter in the URL.  The limit value,
whether specified or applied by default, will be reflected in the data
returned.

`/api/v1/host/[hostname]/events/?limit=50`

## Paging ##

In conjuction with limits, a particular page of data can be requested with
the page parameter.

`/api/v1/host/[hostname]/events/?limit=20&page=2`

## Expansion ##

When requesting data, such as a quest, you can choose to automatically
expand and include data of children data, such as labors, using the expand
parameter.

Multiple expansion parameters can be used.

`/api/v1/quests/[questid]/?expand=labors&expand=events`

## GETs ##

### Hosts ###

To get host data, use `/api/v1/hosts/[hostname]/`

    {
        id: int,
        hostname: string,
        limit: int,
        page: int,
        lastEvent: timestamp,
        events: [],
        labors: [],
        quests: [],
    }

To get all hosts, use `/api/v1/hosts/` (with an appropriate limit and page)

    {
        limit: int,
        page: int,
        totalHosts: int,
        hosts: [],
    }

### Event Types ###

To get event types, use `/api/v1/eventtypes/`

    {
        limit: int,
        page: int,
        totalEventTypes: int,
        eventTypes: [
            {
                id: int,
                category: string,
                state: string,
                description: string,
            },
            ...
        ],
    }

### Events ###

To get events, use `/api/v1/events/`

    {
        limit: int,
        page: int,
        totalEvents: int,
        events: [
            {
                id: int,
                host: {
                    id: int,
                    hostname: string,
                },
                timestamp: timestamp,
                user: string,
                eventType: {
                    id: int,
                    category: string,
                    state: string,
                    description: string,
                },
                note: string,
            },
            ...
        ],
    }

Events can also be expanded in other queries, like host queries.  Never
expand both host and event in a query or you will trigger infinite
expansion.

### Fates ###

To get fates, use `/api/v1/fates`

    {
        limit: int,
        page: int,
        totalFates: int,
        fates: [
            {
                id: int,
                creationEventType: {
                    id: int,
                    category: string,
                    state: string,
                    description: string,
                },
                completionEventType: {
                    id: int,
                    category: string,
                    state: string,
                    description: string,
                },
                intermediate: true|false,
                description: string,
            },
            ...
        ],
    }

### Labors ###

To get laboes, use `/api/v1/labors/`

    {
        limit: int,
        page: int,
        totalFates: int,
        labors: [
            {
                id: int,
                quest: {
                    id: int,
                    embarkTime: timestamp,
                    completionTime: timestamp,
                    creator: string,
                    description: string,
                },
                host: {
                    id: int,
                    hostname: string,
                },
                creationTime: timestamp,
                ackTime: timestamp,
                ackUser: string,
                completionTime: timestamp,
                creationEvent: {
                    id: int,
                    timestamp: timestamp,
                    user: string,
                    note: string,
                },
                completionEvent: {
                    id: int,
                    timestamp: timestamp,
                    user: string,
                    note: string,
                },
            },
            ...
        ],
    }
