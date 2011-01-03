#!/usr/bin/ruby

# Hacker News sometimes goes down or takes too long to respond, so, bail if that happens

exit if File.new(File.expand_path(File.dirname(__FILE__)) + "/latest.rss").stat.zero?

require 'rubygems'
gem 'hpricot', '= 0.6'
require 'feed-normalizer'
require 'open-uri'
require 'erb'

# ActiveSupport has some dooky-ass issue with motherfucking Hpricot
class String
  def blank?
    self !~ /\S/
  end
  def new_york_times_get_over_your_pretentious_bullshit_please
    self.gsub!(/’/, "'")
    self.gsub!(/“/, "\"")
    self.gsub!(/”/, "\"")
    self.gsub!(/—/, "-")
    self.gsub!(/–/, "-")
  end
end


def render_partial_story(story_number, header_number)
  story = @stories[story_number]
  partial =<<PARTIAL
	<a><h<%= header_number %>><%= story.headline %></h<%= header_number %>></a>

	<% unless story.text.blank? %>
	<p>
	  <%= story.text %>
	</p>
	<% end %>

	<p>
	  <strong><a href="<%= story.url %>"><%= story.domain %></a></strong>
	</p>
PARTIAL
  ERB.new(partial).result(binding)
end

class Story < Struct.new(:headline, :domain, :url, :text) ; end

File.open(File.expand_path(File.dirname(__FILE__)) + "/../public/index.html", "w") do |file|
  feed = FeedNormalizer::FeedNormalizer.parse(File.read(File.expand_path(File.dirname(__FILE__)) + "/latest.rss"))
  feed.clean!

  @stories = (feed.entries.collect do |entry|
    next unless entry.url && entry.title

    title = entry.title
    comments_regex = /<a href="http:\/\/news\.ycombinator\.com\/item\?id=\d+">Comments<\/a>/
    comments_url = comments_regex.match(entry.content)
    # now we have the comments_url. however, this is not featured anywhere in the output or the template. this is
    # an intentional move for the sake of quality control. I'm considering adding a comments link, but what might
    # be a lot better is to add a feature which scrapes the comments_url for comments from patio11, peterc, pg, maxklein,
    # etc., so you can estimate at a glance whether the comments are worth reading or not
    entry.content.gsub!(comments_regex, "")
    text = Hpricot(entry.content).to_plain_text
    [text, title].each do |string|
      string.new_york_times_get_over_your_pretentious_bullshit_please
    end
    text.gsub!(/^!\[CDATA\[http:\/\/news\.ycombinator\.com\/item\?id=\d+\]/, "")
    text.gsub!(/\[[^\[]+\]/, "")
    text = text[0..300]

    match = /http:\/\/([^\/]+)\//.match(entry.url)
    match ? domain = match[1] : next

    banned = %w{techcrunch
                codinghorror
                steve-yegge
                skorks
                sheddingbikes
                oppugn.us}.inject(false) do |memo, frequent_timewaster|
      domain.include?(frequent_timewaster) ? true : memo
    end
    banned = true if /zed shaw/i =~ text
    banned = true if /zed shaw/i =~ title
    next if banned

    # avoiding a shit-ton of Unicode
    text = "" if domain =~ /wikipedia/

    Story.new(title, domain, entry.url, text)
  end).compact
  
  file.puts ERB.new(File.read(File.expand_path(File.dirname(__FILE__)) + "/template.erb")).result(binding)
end

