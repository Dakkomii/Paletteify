drop table if exists posts;
drop table if exists users;


create table users(
  profile_id text PRIMARY KEY,
  username text NOT NULL,
  image text NOT NULL,
  background1 text,
  background2 text,
  liked_posts int[] DEFAULT ARRAY[]::integer[]
 );

create table posts(
  post_id SERIAL PRIMARY KEY,
  username text,
  filename text,
  data bytea,
  rgb_1 text DEFAULT '0',
  rgb_2 text DEFAULT '0',
  rgb_3 text DEFAULT '0',
  avg_color_name text,
  average_rgb text DEFAULT '0',
  metadata text DEFAULT 'none',
  typedata text DEFAULT 'none',
  profile_id text,
  description text
);

drop function if exists get_colors(text);
create function get_colors(color text)
  returns int[]
  language plpgsql
as
$$
declare
  colors_len int  := char_length(color) - 5;
  colors     text := substring(color from 5 for colors_len);
  red   int := split_part(colors, ',', 1)::int;
  green int := split_part(colors, ',', 2)::int;
  blue  int := split_part(colors, ',', 3)::int;
begin
  return array[red, green, blue];
end;
$$;

drop function if exists color_distance(text, text);
create function color_distance(color1 text, color2 text)
  returns real
  language plpgsql
as
$$
declare
  colors_1 int[] := get_colors(color1);
  colors_2 int[] := get_colors(color2);
  red_diff int   := colors_1[1] - colors_2[1];
  green_diff int := colors_1[2] - colors_2[2];
  blue_diff int  := colors_1[3] - colors_2[3];
begin
  return sqrt(power(red_diff, 2) + power(green_diff, 2) + power(blue_diff, 2));
end;
$$;
